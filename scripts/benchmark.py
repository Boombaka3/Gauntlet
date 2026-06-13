# scripts/benchmark.py
"""
Offline benchmark for EvidenceTrace conflict detection.

Evaluates judge_conflict_text() against two ground-truth datasets:
  - scripts/test_data/benchmark_records.jsonl  (15 SciFact/PubMedQA/QASPER records)
  - scripts/test_data/conflict_pairs_ground_truth.jsonl  (5 manual cross-document pairs)

Metrics reported:
  - Verdict accuracy (overall + per source_dataset)
  - Verdict confusion matrix
  - Error-type Jaccard overlap (predicted vs target_error_types)

Usage:
  uv run python scripts/benchmark.py
  uv run python scripts/benchmark.py --limit 5
  uv run python scripts/benchmark.py --dataset scifact
  uv run python scripts/benchmark.py --out scripts/test_data/benchmark_results.jsonl

Requires ANTHROPIC_API_KEY in .env.
Exit 0 on completion (regardless of score), 1 on setup failure.
"""
import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

# Minimal Django setup — only needed for importing scoring modules.
import django
django.setup()

from apps.evidence.scoring.conflict_judge import judge_conflict_text
from apps.evidence.utils.dataset_loader import (
    load_benchmark_records,
    load_conflict_pairs,
)

# ── Gold-label normalisation ──────────────────────────────────────────────────

_SUPPORT_LABELS = {"support", "supports", "supported", "true", "yes"}
_CONTRADICT_LABELS = {"contradict", "contradicts", "contradicted",
                      "conflict", "conflict_or_conditionally_supported",
                      "false", "no"}


def _gold_to_verdict(gold: str) -> str:
    g = str(gold).lower().strip()
    if g in _SUPPORT_LABELS:
        return "SUPPORTS"
    if g in _CONTRADICT_LABELS:
        return "CONTRADICTS"
    return "NEI"


# ── Record normalisation ──────────────────────────────────────────────────────

def _sentences_text(doc: dict) -> str:
    if not doc:
        return ""
    sents = doc.get("sentences") or []
    if sents:
        return " ".join(s.strip() for s in sents if s.strip())
    return (doc.get("abstract") or "").strip()


def _flatten_records(records: list[dict]) -> list[dict]:
    """Return a normalised list with consistent keys for benchmarking."""
    out = []
    for r in records:
        doc_a = r.get("document_a") or {}
        doc_b = r.get("document_b") or {}
        text_a = _sentences_text(doc_a)
        text_b = _sentences_text(doc_b)

        # For claim-verification records (document_b is null):
        # treat the input_claim_or_question as text_a, document_a as text_b.
        if not text_b:
            text_a = r.get("input_claim_or_question", "")
            text_b = _sentences_text(doc_a)

        out.append({
            "id": r.get("id", ""),
            "source_dataset": r.get("source_dataset", ""),
            "task_type": r.get("task_type", ""),
            "title_a": doc_a.get("title", "") or "Claim",
            "title_b": doc_b.get("title", "") or doc_a.get("title", "") or "Document",
            "text_a": text_a,
            "text_b": text_b,
            "gold_verdict": _gold_to_verdict(r.get("gold_label", "")),
            "target_error_types": r.get("target_error_types") or [],
        })
    return out


# ── Metrics ───────────────────────────────────────────────────────────────────

def _jaccard(a: list, b: list) -> float:
    sa, sb = set(a), set(b)
    if not sa and not sb:
        return 1.0
    inter = len(sa & sb)
    union = len(sa | sb)
    return inter / union if union else 0.0


def _accuracy(preds: list[str], golds: list[str]) -> float:
    if not preds:
        return 0.0
    return sum(p == g for p, g in zip(preds, golds)) / len(preds)


def _confusion(preds: list[str], golds: list[str]) -> dict:
    matrix: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for p, g in zip(preds, golds):
        matrix[g][p] += 1
    return {k: dict(v) for k, v in matrix.items()}


def _print_confusion(matrix: dict) -> None:
    all_labels = sorted({k for row in matrix.values() for k in row} | set(matrix.keys()))
    col_w = max(len(l) for l in all_labels) + 2
    row_label = "Gold \\ Pred"
    header = f"{row_label:<16}" + "".join(f"{l:>{col_w}}" for l in all_labels)
    print(header)
    print("-" * len(header))
    for gold in all_labels:
        row = matrix.get(gold, {})
        line = f"{gold:<16}" + "".join(f"{row.get(pred, 0):>{col_w}}" for pred in all_labels)
        print(line)


# ── Main ──────────────────────────────────────────────────────────────────────

def run_benchmark(
    records: list[dict],
    limit: int | None,
    out_path: Path | None,
) -> list[dict]:
    if limit:
        records = records[:limit]

    results = []
    for i, rec in enumerate(records, 1):
        print(
            f"  [{i}/{len(records)}] {rec['id']}  "
            f"({rec['source_dataset']})  gold={rec['gold_verdict']}",
            end=" ... ",
            flush=True,
        )
        try:
            pred = judge_conflict_text(
                text_a=rec["text_a"],
                text_b=rec["text_b"],
                title_a=rec["title_a"],
                title_b=rec["title_b"],
            )
            verdict = pred.get("verdict", "NEI")
            error_types = pred.get("error_types", [])
            jaccard = _jaccard(error_types, rec["target_error_types"])
            correct = verdict == rec["gold_verdict"]
            print(f"pred={verdict}  {'OK' if correct else 'WRONG'}  jaccard={jaccard:.2f}")
        except Exception as e:
            verdict = "NEI"
            error_types = []
            jaccard = 0.0
            correct = verdict == rec["gold_verdict"]
            pred = {}
            print(f"ERROR: {e}")

        results.append({
            "id": rec["id"],
            "source_dataset": rec["source_dataset"],
            "task_type": rec["task_type"],
            "gold_verdict": rec["gold_verdict"],
            "pred_verdict": verdict,
            "correct": correct,
            "target_error_types": rec["target_error_types"],
            "pred_error_types": error_types,
            "error_type_jaccard": jaccard,
            "reasoning": pred.get("reasoning", ""),
        })

    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w", encoding="utf-8") as f:
            for row in results:
                f.write(json.dumps(row) + "\n")
        print(f"\nResults written to {out_path}")

    return results


def print_report(results: list[dict]) -> None:
    if not results:
        print("No results.")
        return

    preds = [r["pred_verdict"] for r in results]
    golds = [r["gold_verdict"] for r in results]

    overall_acc = _accuracy(preds, golds)
    avg_jaccard = sum(r["error_type_jaccard"] for r in results) / len(results)

    print(f"\n{'=' * 60}")
    print(f"BENCHMARK RESULTS  ({len(results)} records)")
    print(f"{'=' * 60}")
    print(f"  Overall verdict accuracy : {overall_acc:.3f} ({sum(r['correct'] for r in results)}/{len(results)})")
    print(f"  Avg error-type Jaccard   : {avg_jaccard:.3f}")

    # Per-dataset breakdown
    by_dataset: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_dataset[r["source_dataset"]].append(r)

    print(f"\n  Per-dataset accuracy:")
    for ds, recs in sorted(by_dataset.items()):
        ds_preds = [r["pred_verdict"] for r in recs]
        ds_golds = [r["gold_verdict"] for r in recs]
        ds_acc = _accuracy(ds_preds, ds_golds)
        print(f"    {ds:<35} {ds_acc:.3f}  ({sum(r['correct'] for r in recs)}/{len(recs)})")

    # Verdict distribution
    print(f"\n  Predicted verdict distribution:")
    for verdict, count in sorted(Counter(preds).items()):
        print(f"    {verdict:<15} {count}")

    print(f"\n  Confusion matrix (rows=gold, cols=pred):")
    matrix = _confusion(preds, golds)
    _print_confusion(matrix)

    # Error type breakdown
    all_target = [t for r in results for t in r["target_error_types"]]
    all_pred_et = [t for r in results for t in r["pred_error_types"]]
    if all_target:
        print(f"\n  Target error-type frequency:")
        for et, cnt in Counter(all_target).most_common():
            print(f"    {et:<40} {cnt}")
        print(f"\n  Predicted error-type frequency:")
        for et, cnt in Counter(all_pred_et).most_common(10):
            print(f"    {et:<40} {cnt}")

    print(f"\n{'=' * 60}")


def main() -> None:
    parser = argparse.ArgumentParser(description="EvidenceTrace conflict-detection benchmark")
    parser.add_argument("--limit", type=int, default=None, help="Max records to evaluate")
    parser.add_argument(
        "--dataset",
        type=str,
        default=None,
        help="Filter by source_dataset (case-insensitive substring match)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Path to write per-record JSONL results",
    )
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key or api_key in ("sk-ant-...", "placeholder", ""):
        print("ERROR: ANTHROPIC_API_KEY not set in .env — benchmark requires Claude API.")
        sys.exit(1)

    print("Loading benchmark records...")
    benchmark = _flatten_records(load_benchmark_records())
    conflict_pairs = _flatten_records(load_conflict_pairs())
    all_records = benchmark + conflict_pairs
    print(f"  benchmark_records.jsonl  : {len(benchmark)} records")
    print(f"  conflict_pairs.jsonl     : {len(conflict_pairs)} records")
    print(f"  Total                    : {len(all_records)} records")

    if args.dataset:
        ds_filter = args.dataset.lower()
        all_records = [r for r in all_records if ds_filter in r["source_dataset"].lower()]
        print(f"  After --dataset filter   : {len(all_records)} records")

    if not all_records:
        print("No records to evaluate after filtering.")
        sys.exit(0)

    out_path = Path(args.out) if args.out else None

    print(f"\nRunning benchmark (n={min(args.limit or len(all_records), len(all_records))})...\n")
    results = run_benchmark(all_records, limit=args.limit, out_path=out_path)
    print_report(results)


if __name__ == "__main__":
    main()
