# llm_eval_harness/apps/evals/scoring/rubric.py
import json
import logging
import os
from pathlib import Path

from apps.evals.models import ModelRun, ScoreResult

logger = logging.getLogger(__name__)

JUDGE_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "judge_score.txt"
JUDGE_MODEL = os.getenv("CLAUDE_JUDGE_MODEL", "claude-sonnet-4-6")
PASS_OVERALL_THRESHOLD = 0.6  # 3/5 normalized


def score_rubric(model_run: ModelRun, rubric: list[dict]) -> ScoreResult:
    """
    Calls Claude as judge using judge_score.txt.
    Returns an UNSAVED ScoreResult with per-criterion scores and weighted overall (0-1).
    """
    template = JUDGE_PROMPT_PATH.read_text(encoding="utf-8")
    prompt = template.format(
        system_prompt=model_run.prompt_case.system_prompt,
        user_prompt=model_run.prompt_case.user_prompt,
        model_output=model_run.raw_output,
        rubric_criteria=json.dumps(rubric, indent=2),
    )

    raw_response = ""
    reasoning = ""
    scores: dict = {}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_response = response.content[0].text.strip() if response.content else "{}"
        parsed = json.loads(raw_response)
        scores = parsed.get("scores", {})
        reasoning = parsed.get("reasoning", "")
    except json.JSONDecodeError:
        logger.error(
            "Rubric judge returned non-JSON for ModelRun %s: %r",
            model_run.id,
            raw_response,
        )
        reasoning = f"JSON parse error — raw response: {raw_response[:200]}"
    except Exception as exc:
        logger.error("score_rubric failed for ModelRun %s: %s", model_run.id, exc)
        reasoning = str(exc)

    overall = _weighted_overall(scores, rubric)
    passed = overall >= PASS_OVERALL_THRESHOLD

    return ScoreResult(
        model_run=model_run,
        scores=scores,
        overall=round(overall, 4),
        passed=passed,
        judge_reasoning=reasoning,
    )


def _weighted_overall(scores: dict, rubric: list[dict]) -> float:
    """Weighted average of criterion scores (1-5), normalized to 0-1."""
    if not rubric or not scores:
        return 0.0

    total_weight = sum(float(c.get("weight", 1.0)) for c in rubric)
    if total_weight == 0:
        return 0.0

    weighted_sum = 0.0
    for criterion in rubric:
        name = criterion.get("criterion", "")
        weight = float(criterion.get("weight", 1.0))
        raw_score = scores.get(name, 1)
        try:
            score = float(raw_score)
        except (TypeError, ValueError):
            score = 1.0
        score = max(1.0, min(5.0, score))  # clamp to [1, 5]
        weighted_sum += score * weight

    # normalize: max possible weighted_sum = 5 * total_weight → divide by (5 * total_weight)
    return weighted_sum / (5.0 * total_weight)
