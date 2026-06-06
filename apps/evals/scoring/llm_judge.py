# llm_eval_harness/apps/evals/scoring/llm_judge.py
import json
import logging
import os
from pathlib import Path

from apps.evals.models import ModelRun, ScoreResult
from apps.evals.scoring.rubric import score_rubric

logger = logging.getLogger(__name__)

JUDGE_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "judge_score.txt"
JUDGE_MODEL = os.getenv("CLAUDE_JUDGE_MODEL", "claude-sonnet-4-6")

_SIMPLE_RUBRIC = [{"criterion": "Quality", "weight": 1.0}]
_SIMPLE_PROMPT_SUFFIX = """
Rate the overall quality of the model output on a scale of 1-5 where:
1 = Very poor  2 = Poor  3 = Adequate  4 = Good  5 = Excellent
"""


def score_llm_judge(model_run: ModelRun) -> ScoreResult:
    """
    Delegates to score_rubric when the suite has rubric criteria.
    Falls back to a single-criterion 'Quality' rubric when none are defined.
    Returns an UNSAVED ScoreResult.
    """
    rubric = model_run.prompt_case.suite.rubric
    if rubric:
        return score_rubric(model_run, rubric)

    # Simple pass/fail path — no rubric defined on the suite
    template = JUDGE_PROMPT_PATH.read_text(encoding="utf-8")
    simple_rubric_json = json.dumps(_SIMPLE_RUBRIC, indent=2)
    prompt = (
        template.format(
            system_prompt=model_run.prompt_case.system_prompt,
            user_prompt=model_run.prompt_case.user_prompt,
            model_output=model_run.raw_output,
            rubric_criteria=simple_rubric_json + _SIMPLE_PROMPT_SUFFIX,
        )
    )

    raw_response = ""
    reasoning = ""
    scores: dict = {}

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))
        response = client.messages.create(
            model=JUDGE_MODEL,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_response = response.content[0].text.strip() if response.content else "{}"
        parsed = json.loads(raw_response)
        scores = parsed.get("scores", {})
        reasoning = parsed.get("reasoning", "")
    except json.JSONDecodeError:
        logger.error(
            "LLM judge returned non-JSON for ModelRun %s: %r",
            model_run.id,
            raw_response,
        )
        return ScoreResult(
            model_run=model_run,
            scores={},
            overall=None,
            passed=None,
            judge_reasoning=f"judge_unavailable: JSON parse error — raw: {raw_response[:200]}",
        )
    except Exception as exc:
        logger.error("score_llm_judge failed for ModelRun %s: %s", model_run.id, exc)
        return ScoreResult(
            model_run=model_run,
            scores={},
            overall=None,
            passed=None,
            judge_reasoning=f"judge_unavailable: {exc}",
        )

    raw_score = float(scores.get("Quality", 1))
    raw_score = max(1.0, min(5.0, raw_score))
    overall = round((raw_score - 1) / 4.0, 4)  # map [1,5] → [0,1]
    passed = raw_score >= 3.0

    return ScoreResult(
        model_run=model_run,
        scores=scores,
        overall=overall,
        passed=passed,
        judge_reasoning=reasoning,
    )
