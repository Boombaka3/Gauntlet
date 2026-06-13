#!/usr/bin/env python
"""
Download SciFact, PubMedQA, and QASPER datasets and normalize to EvidenceLens schema.
Saves to scripts/test_data/benchmark_records.jsonl (overwrites existing 15-record sample).

Schema mirrors EvidenceLens normalize_*.py scripts exactly:
  id, source_dataset, task_type, input_claim_or_question,
  document_a {doc_id, title, abstract, sentences, metadata},
  document_b (null), gold_label, gold_evidence, target_error_types

Data sources (direct S3 — avoids HuggingFace legacy loading scripts):
  SciFact : https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz
  QASPER  : https://qasper-dataset.s3.us-west-2.amazonaws.com/qasper-train-dev-v0.3.tgz
  PubMedQA: HuggingFace qiaojin/PubMedQA pqa_labeled (1000 labeled records)
"""
import io
import json
import sys
import tarfile
import urllib.request
from pathlib import Path

OUTPUT_PATH = Path(__file__).resolve().parent / "test_data" / "benchmark_records.jsonl"
OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

records = []

# ── SciFact error map (mirrors normalize_scifact.py) ─────────────────────────
_SCIFACT_ERROR_MAP = {
    "CONTRADICT": ["unsupported_claim", "contradiction_with_source"],
    "SUPPORT":    ["wrong_evidence", "missing_evidence"],
    "default":    ["missing_evidence", "false_certainty"],
}

# ── PubMedQA error map (mirrors normalize_pubmedqa.py) ───────────────────────
_PUBMEDQA_ERROR_MAP = {
    "maybe": ["false_certainty", "missing_limitation"],
    "yes":   ["overgeneralization", "condition_dropping"],
    "no":    ["overgeneralization", "condition_dropping"],
}

# ── SciFact (direct S3 tarball — the URL from the HF loading script) ──────────
print("Downloading SciFact...")
try:
    _SCIFACT_URL = "https://scifact.s3-us-west-2.amazonaws.com/release/latest/data.tar.gz"
    print("  Fetching tarball...", flush=True)
    with urllib.request.urlopen(_SCIFACT_URL, timeout=120) as resp:
        raw_bytes = resp.read()

    # Extract to memory
    tar_obj = tarfile.open(fileobj=io.BytesIO(raw_bytes), mode="r:gz")
    tar_members = {m.name: m for m in tar_obj.getmembers() if m.isfile()}

    def _read_tar_jsonl(name_fragment: str) -> list[dict]:
        for name, member in tar_members.items():
            if name_fragment in name:
                f = tar_obj.extractfile(member)
                if f:
                    return [json.loads(line) for line in f.read().decode("utf-8").splitlines() if line.strip()]
        return []

    corpus_rows = _read_tar_jsonl("corpus.jsonl")
    corpus_map = {str(row["doc_id"]): row for row in corpus_rows}
    print(f"  corpus: {len(corpus_map)} docs")

    scifact_count = 0
    for fname_frag, split_name in [("claims_train.jsonl", "train"), ("claims_dev.jsonl", "validation")]:
        claims = _read_tar_jsonl(fname_frag)
        for claim in claims:
            evidence = claim.get("evidence", {})
            if not evidence:
                continue

            doc_id = list(evidence.keys())[0]
            ev_entries = evidence[doc_id]
            label_raw = ev_entries[0]["label"]
            sent_idxs = ev_entries[0]["sentences"]

            gold_label = "support" if label_raw == "SUPPORT" else "contradict"

            doc = corpus_map.get(str(doc_id), {})
            abstract_list = doc.get("abstract", [])
            if isinstance(abstract_list, str):
                abstract_list = [abstract_list]

            ev_sents = [abstract_list[i] for i in sent_idxs if i < len(abstract_list)]
            gold_evidence = " ".join(ev_sents)
            error_types = _SCIFACT_ERROR_MAP.get(label_raw, _SCIFACT_ERROR_MAP["default"])

            records.append({
                "id": f"scifact_{claim['id']}_{split_name}",
                "source_dataset": "SciFact",
                "task_type": "claim_verification",
                "input_claim_or_question": claim.get("claim", ""),
                "document_a": {
                    "doc_id": str(doc_id),
                    "title": doc.get("title", ""),
                    "abstract": " ".join(abstract_list),
                    "sentences": abstract_list,
                    "metadata": {},
                },
                "document_b": None,
                "gold_label": gold_label,
                "gold_evidence": gold_evidence,
                "target_error_types": error_types,
            })
            scifact_count += 1

    print(f"  SciFact: {scifact_count} records")

except Exception as e:
    print(f"  SciFact FAILED: {e}")

# ── PubMedQA ──────────────────────────────────────────────────────────────────
print("Downloading PubMedQA...")
try:
    from datasets import load_dataset

    pubmedqa_ds = load_dataset("qiaojin/PubMedQA", "pqa_labeled")
    pubmedqa_count = 0

    for split in ["train"]:
        if split not in pubmedqa_ds:
            continue
        for row in pubmedqa_ds[split]:
            pubmed_id = str(row.get("pubid", ""))
            question = row.get("question", "")
            contexts = row.get("context", {})
            long_answer = row.get("long_answer", "")
            final_decision = str(row.get("final_decision", "maybe")).lower()
            year = str(row.get("year", "")) if row.get("year") else ""
            meshes = row.get("meshes", []) or []

            # contexts is a dict {"labels": [...], "sentences": [[...], ...], "meshes": [...]}
            # Flatten to list of sentence strings matching EvidenceLens schema
            if isinstance(contexts, dict):
                sentence_groups = contexts.get("sentences", [])
                flat_sentences = []
                for group in sentence_groups:
                    if isinstance(group, list):
                        flat_sentences.extend(group)
                    elif isinstance(group, str):
                        flat_sentences.append(group)
                sentences_list = flat_sentences
            elif isinstance(contexts, list):
                sentences_list = [str(s) for s in contexts]
            else:
                sentences_list = [str(contexts)] if contexts else []

            records.append({
                "id": f"pubmedqa_{pubmed_id}",
                "source_dataset": "PubMedQA",
                "task_type": "biomedical_qa",
                "input_claim_or_question": question,
                "document_a": {
                    "doc_id": pubmed_id,
                    "title": "",
                    "abstract": long_answer,
                    "sentences": sentences_list,
                    "metadata": {"year": year, "meshes": meshes},
                },
                "document_b": None,
                "gold_label": final_decision,
                "gold_evidence": long_answer,
                "target_error_types": _PUBMEDQA_ERROR_MAP.get(
                    final_decision, ["false_certainty", "missing_limitation"]
                ),
            })
            pubmedqa_count += 1

    print(f"  PubMedQA: {pubmedqa_count} records")

except Exception as e:
    print(f"  PubMedQA FAILED: {e}")

# ── QASPER (direct S3 tarball — the URL from the HF loading script) ───────────
print("Downloading QASPER...")
try:
    _QASPER_URL = "https://qasper-dataset.s3.us-west-2.amazonaws.com/qasper-train-dev-v0.3.tgz"

    print("  Fetching tarball...", flush=True)
    with urllib.request.urlopen(_QASPER_URL, timeout=120) as resp:
        raw_bytes = resp.read()

    tar_obj = tarfile.open(fileobj=io.BytesIO(raw_bytes), mode="r:gz")
    tar_members = {m.name: m for m in tar_obj.getmembers() if m.isfile()}
    print(f"  tar contents: {list(tar_members.keys())}")

    qasper_count = 0
    for split_name, json_frag in [("train", "train"), ("validation", "dev")]:
        matching = {n: m for n, m in tar_members.items() if json_frag in n and n.endswith(".json")}
        if not matching:
            print(f"  QASPER {split_name}: no matching file in tarball")
            continue

        member = next(iter(matching.values()))
        f = tar_obj.extractfile(member)
        if not f:
            continue
        data = json.loads(f.read().decode("utf-8"))

        for paper_id, paper in data.items():
            title    = paper.get("title", "") or ""
            abstract = paper.get("abstract", "") or ""
            sentences = [s.strip() for s in abstract.split(".") if s.strip()]
            qas = paper.get("qas", []) or []

            for i, qa in enumerate(qas):
                question = (qa.get("question") or "").strip()
                if not question:
                    continue

                answers = qa.get("answers", []) or []

                if all(
                    (a.get("answer") or {}).get("unanswerable", True)
                    for a in answers
                ):
                    continue

                first_valid = None
                for a in answers:
                    ans = a.get("answer") or {}
                    if not ans.get("unanswerable", True):
                        first_valid = ans
                        break

                if first_valid is None:
                    continue

                free_form  = first_valid.get("free_form_answer", "") or ""
                extractive = first_valid.get("extractive_spans", []) or []

                records.append({
                    "id": f"qasper_{paper_id}_q{i}",
                    "source_dataset": "QASPER",
                    "task_type": "paper_qa",
                    "input_claim_or_question": question,
                    "document_a": {
                        "doc_id": paper_id,
                        "title": title,
                        "abstract": abstract,
                        "sentences": sentences,
                        "metadata": {},
                    },
                    "document_b": None,
                    "gold_label": "see_answer",
                    "gold_evidence": json.dumps({
                        "answer":   free_form,
                        "evidence": extractive,
                    }, ensure_ascii=False),
                    "target_error_types": [
                        "missing_evidence",
                        "unsupported_claim",
                        "paper_section_misread",
                    ],
                })
                qasper_count += 1

    print(f"  QASPER: {qasper_count} records")

except Exception as e:
    print(f"  QASPER FAILED: {e}")

# ── Save ──────────────────────────────────────────────────────────────────────
print(f"\nTotal records: {len(records)}")
counts: dict[str, int] = {}
for r in records:
    ds = r["source_dataset"]
    counts[ds] = counts.get(ds, 0) + 1
for ds, count in counts.items():
    print(f"  {ds}: {count}")

if not records:
    print("ERROR: no records downloaded — aborting without overwriting existing file")
    sys.exit(1)

with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
    for record in records:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

print(f"\nSaved to {OUTPUT_PATH}")
print("Done.")
