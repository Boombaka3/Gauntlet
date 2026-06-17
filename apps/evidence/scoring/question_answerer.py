# apps/evidence/scoring/question_answerer.py
import os
import re
import json
import logging
from pathlib import Path
from apps.evidence.models import Paper, AnswerRecord
from apps.evidence.adapters.openai import OpenAICompatAdapter

logger = logging.getLogger(__name__)

PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "question_answerer.txt"
PROMPT_TEMPLATE = PROMPT_PATH.read_text(encoding="utf-8")

VALID_ANSWERS = {"yes", "no", "maybe"}


def _get_adapter() -> OpenAICompatAdapter:
    model = os.environ.get("NAVIGATOR_MODEL", "llama-3.3-70b-instruct")
    return OpenAICompatAdapter(model_id=model)


def _strip_fences(text: str) -> str:
    text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
    text = re.sub(r'```\s*$', '', text, flags=re.MULTILINE)
    return text.strip()


def _parse_response(raw: str) -> dict:
    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        return {
            "answer": "maybe",
            "reasoning": "parse error",
            "source_sentence": "",
            "confidence": None,
            "error_types": [],
        }
    answer = str(data.get("answer", "maybe")).lower().strip()
    if answer not in VALID_ANSWERS:
        answer = "maybe"
    return {
        "answer": answer,
        "reasoning": str(data.get("reasoning", ""))[:500],
        "source_sentence": str(data.get("source_sentence", ""))[:500],
        "confidence": _clamp(data.get("confidence")),
        "error_types": [
            e for e in data.get("error_types", [])
            if isinstance(e, str)
        ],
    }


def _clamp(v) -> float | None:
    if v is None:
        return None
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return None


def answer_question(paper: Paper, question: str) -> AnswerRecord:
    """
    Ask a yes/no/maybe question about a paper using its abstract.
    Returns an unsaved AnswerRecord.
    """
    abstract = paper.abstract or " ".join(
        paper.parsed_sections.get(k, "")
        for k in ("abstract", "body")
        if paper.parsed_sections.get(k)
    )
    prompt = PROMPT_TEMPLATE.format(
        question=question.strip(),
        abstract=abstract[:3000],
    )
    try:
        adapter = _get_adapter()
        result = adapter.complete(
            system_prompt=(
                "You are a biomedical research question answerer. "
                "Respond only with valid JSON."
            ),
            user_prompt=prompt,
            max_tokens=512,
        )
        if result.error:
            logger.error(f"Adapter error: {result.error}")
            parsed = _parse_response("")
        else:
            parsed = _parse_response(result.output or "")
    except Exception as e:
        logger.error(f"answer_question failed: {e}")
        parsed = _parse_response("")

    return AnswerRecord(
        paper=paper,
        question=question.strip(),
        answer=parsed["answer"],
        reasoning=parsed["reasoning"],
        source_sentence=parsed["source_sentence"],
        error_types=parsed["error_types"],
    )


def answer_question_text(question: str,
                         abstract: str,
                         gold_label: str = "") -> dict:
    """
    Text-only version for benchmarking. No ORM objects created.
    Returns dict with answer, reasoning, source_sentence, confidence, error_types.
    """
    prompt = PROMPT_TEMPLATE.format(
        question=question.strip(),
        abstract=abstract[:3000],
    )
    try:
        adapter = _get_adapter()
        result = adapter.complete(
            system_prompt=(
                "You are a biomedical research question answerer. "
                "Respond only with valid JSON."
            ),
            user_prompt=prompt,
            max_tokens=512,
        )
        parsed = _parse_response(result.output or "" if not result.error else "")
    except Exception as e:
        logger.error(f"answer_question_text failed: {e}")
        parsed = _parse_response("")
    return parsed
