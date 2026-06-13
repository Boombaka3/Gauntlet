# apps/evidence/scoring/faithfulness.py
import json
import os
import re

import anthropic

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

_FAITHFULNESS_PROMPT = """\
You are a scientific evidence auditor.
Audit whether the extracted claim below is faithful to its source sentence.

SOURCE SENTENCE:
{source_sentence}

CLAIM:
{claim_text}

Return ONLY valid JSON. No preamble, no markdown fences.

{
  "faithful": true or false,
  "faithfulness_score": 0.0,
  "support_label": "supported | contradicted | partially_supported | uncertain | insufficient",
  "overgeneralization": true or false,
  "false_certainty": true or false,
  "error_types": ["list from: overgeneralization, condition_dropping, false_certainty, missing_evidence, unsupported_claim, wrong_evidence, missing_limitation, contradiction_with_source, conflict_ignored, paper_section_misread"],
  "reasoning": "one sentence explaining the main finding"
}

Rules:
- faithfulness_score: 0.0-1.0, where 1.0 means perfectly faithful to the source
- overgeneralization: true if claim removes population, dataset, or condition limits from source
- false_certainty: true if claim says yes/no when source says maybe or uncertain
- error_types: only include types actually present; return [] if claim is clean
Return only valid JSON. No explanation outside the JSON.
"""


def _strip_fences(text: str) -> str:
    return re.sub(r"```(?:json)?|```", "", text).strip()


def score_faithfulness(claim_text: str, source_sentence: str) -> dict:
    """
    Returns:
    {
        "faithful": bool | None,
        "faithfulness_score": float | None,  # 0.0-1.0
        "error_types": list[str],            # from 9-type taxonomy
        "reasoning": str
    }
    """
    if not claim_text.strip() or not source_sentence.strip():
        return {
            "faithful": None,
            "faithfulness_score": None,
            "error_types": [],
            "reasoning": "missing input",
        }

    prompt = (
        _FAITHFULNESS_PROMPT
        .replace("{claim_text}", claim_text[:1000])
        .replace("{source_sentence}", source_sentence[:1000])
    )

    try:
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        try:
            data = json.loads(_strip_fences(raw))
        except json.JSONDecodeError:
            data = {}

        raw_errors = data.get("error_types", [])
        error_types = (
            [e for e in raw_errors if e in _VALID_ERROR_TYPES]
            if isinstance(raw_errors, list)
            else []
        )

        raw_score = data.get("faithfulness_score")
        try:
            faithfulness_score = (
                max(0.0, min(1.0, float(raw_score))) if raw_score is not None else None
            )
        except (TypeError, ValueError):
            faithfulness_score = None

        faithful = data.get("faithful")
        if not isinstance(faithful, bool):
            faithful = None

        return {
            "faithful": faithful,
            "faithfulness_score": faithfulness_score,
            "error_types": error_types,
            "reasoning": str(data.get("reasoning", ""))[:500],
        }

    except Exception:
        return {
            "faithful": None,
            "faithfulness_score": None,
            "error_types": [],
            "reasoning": "scoring failed",
        }
