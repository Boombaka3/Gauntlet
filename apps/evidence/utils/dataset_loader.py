# apps/evidence/utils/dataset_loader.py
import json
from pathlib import Path

BASE = Path(__file__).parent.parent.parent.parent / "scripts" / "test_data"


def load_benchmark_records() -> list[dict]:
    path = BASE / "benchmark_records.jsonl"
    if not path.exists():
        return []
    records = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_conflict_pairs() -> list[dict]:
    path = BASE / "conflict_pairs_ground_truth.jsonl"
    if not path.exists():
        return []
    pairs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                pairs.append(json.loads(line))
    return pairs


def load_evidence_audit_outputs() -> list[dict]:
    path = BASE / "evidence_audit_outputs.jsonl"
    if not path.exists():
        return []
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def get_scifact_records() -> list[dict]:
    return [r for r in load_benchmark_records() if r.get("source_dataset") == "SciFact"]


def get_pubmedqa_records() -> list[dict]:
    return [r for r in load_benchmark_records() if r.get("source_dataset") == "PubMedQA"]


def get_qasper_records() -> list[dict]:
    return [r for r in load_benchmark_records() if r.get("source_dataset") == "QASPER"]


def get_conflict_text_pairs() -> list[tuple[str, str, str]]:
    """
    Returns list of (text_a, text_b, ground_truth_verdict) tuples.
    ground_truth_verdict: CONTRADICTS or SUPPORTS
    Extracts text fields from EvidenceLens conflict pair records.
    """
    pairs = load_conflict_pairs()
    result = []
    for p in pairs:
        doc_a = p.get("document_a") or {}
        doc_b = p.get("document_b") or {}
        text_a = " ".join(doc_a.get("sentences", [])) or doc_a.get("abstract", "")
        text_b = " ".join(doc_b.get("sentences", [])) or doc_b.get("abstract", "")
        gold = p.get("gold_label", "")
        # All EvidenceLens conflict pairs use "conflict_or_conditionally_supported"
        verdict = (
            "SUPPORTS"
            if str(gold).lower() in ("support", "supports", "supported", "true")
            else "CONTRADICTS"
        )
        if text_a and text_b:
            result.append((text_a, text_b, verdict))
    return result
