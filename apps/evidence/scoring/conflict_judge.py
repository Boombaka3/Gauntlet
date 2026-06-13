# apps/evidence/scoring/conflict_judge.py
import json
import os
import re
from pathlib import Path

import anthropic

from apps.evidence.models import Claim, ConflictPair

JUDGE_PROMPT = (Path(__file__).parent.parent / "prompts" / "conflict_judge.txt").read_text()

_VALID_ERROR_TYPES = {
    "overgeneralization",
    "condition_dropping",
    "false_certainty",
    "missing_evidence",
    "unsupported_claim",
    "wrong_evidence",
    "missing_limitation",
    "contradiction_with_source",
    "conflict_ignored",
    "paper_section_misread",
}


def _strip_fences(text: str) -> str:
    return re.sub(r"```(?:json)?|```", "", text).strip()


def _call_claude(prompt: str) -> dict:
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    try:
        return json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        return {}


def _parse_response(data: dict) -> dict:
    raw_verdict = data.get("verdict", "NEI").upper()
    verdict = raw_verdict if raw_verdict in ConflictPair.Verdict.values else "NEI"

    raw_ct = data.get("conflict_type", "none").lower()
    conflict_type = raw_ct if raw_ct in ConflictPair.ConflictType.values else "none"

    sev = data.get("severity", 1)
    try:
        severity = max(1, min(5, int(sev)))
    except (TypeError, ValueError):
        severity = 1

    raw_errors = data.get("error_types", [])
    error_types = (
        [e for e in raw_errors if e in _VALID_ERROR_TYPES]
        if isinstance(raw_errors, list)
        else []
    )

    return {
        "verdict": verdict,
        "conflict_type": conflict_type,
        "severity": severity,
        "reasoning": str(data.get("reasoning", ""))[:1000],
        "source_sentence_a": str(data.get("source_sentence_a", ""))[:500],
        "source_sentence_b": str(data.get("source_sentence_b", ""))[:500],
        "error_types": error_types,
    }


def judge_conflict(claim_a: Claim, claim_b: Claim) -> ConflictPair:
    paper_a_title = claim_a.paper.title or f"Paper {claim_a.paper.id}"
    paper_b_title = claim_b.paper.title or f"Paper {claim_b.paper.id}"

    prompt = (
        JUDGE_PROMPT
        .replace("{paper_a_title}", paper_a_title)
        .replace("{claim_a_text}", claim_a.text)
        .replace("{paper_b_title}", paper_b_title)
        .replace("{claim_b_text}", claim_b.text)
    )

    try:
        data = _call_claude(prompt)
    except Exception:
        data = {}

    parsed = _parse_response(data)
    return ConflictPair(
        claim_a=claim_a,
        claim_b=claim_b,
        verdict=parsed["verdict"],
        conflict_type=parsed["conflict_type"],
        severity=parsed["severity"],
        reasoning=parsed["reasoning"],
        source_sentence_a=parsed["source_sentence_a"],
        source_sentence_b=parsed["source_sentence_b"],
        error_types=parsed["error_types"],
    )


def judge_conflict_text(
    text_a: str,
    text_b: str,
    title_a: str = "Paper A",
    title_b: str = "Paper B",
) -> dict:
    """
    Returns dict without creating ORM objects.
    Used by benchmark.py for evaluation against ground truth.
    Returns: {"verdict": str, "conflict_type": str, "severity": int,
              "reasoning": str, "error_types": list}
    """
    prompt = (
        JUDGE_PROMPT
        .replace("{paper_a_title}", title_a)
        .replace("{claim_a_text}", text_a)
        .replace("{paper_b_title}", title_b)
        .replace("{claim_b_text}", text_b)
    )

    try:
        data = _call_claude(prompt)
    except Exception:
        data = {}

    parsed = _parse_response(data)
    return {
        "verdict": parsed["verdict"],
        "conflict_type": parsed["conflict_type"],
        "severity": parsed["severity"],
        "reasoning": parsed["reasoning"],
        "error_types": parsed["error_types"],
    }
