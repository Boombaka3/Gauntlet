# llm_eval_harness/apps/evals/scoring/regression.py
import logging

from apps.evals.models import ModelRun, ScoreResult
from apps.evals.scoring.llm_judge import score_llm_judge

logger = logging.getLogger(__name__)


def score_regression(model_run: ModelRun, baseline_run_id: int) -> ScoreResult:
    """
    Scores the current ModelRun via llm_judge, then computes the delta against
    the corresponding ScoreResult in the baseline run.

    Returns an UNSAVED ScoreResult with regression_delta set.
    If no baseline ScoreResult is found, regression_delta=None and passed=True.
    """
    # Score current output first
    current_result = score_llm_judge(model_run)
    current_overall = current_result.overall

    # Find the baseline ModelRun for the same (prompt_case, model_id)
    baseline_model_run = (
        ModelRun.objects.filter(
            eval_run_id=baseline_run_id,
            prompt_case=model_run.prompt_case,
            model_id=model_run.model_id,
            status=ModelRun.Status.DONE,
        )
        .first()
    )

    if baseline_model_run is None:
        logger.warning(
            "No baseline ModelRun found for prompt_case=%s model_id=%s in EvalRun %s",
            model_run.prompt_case_id,
            model_run.model_id,
            baseline_run_id,
        )
        current_result.regression_delta = None
        current_result.passed = True
        return current_result

    try:
        baseline_score = ScoreResult.objects.get(model_run=baseline_model_run)
    except ScoreResult.DoesNotExist:
        logger.warning(
            "ScoreResult missing for baseline ModelRun %s", baseline_model_run.id
        )
        current_result.regression_delta = None
        current_result.passed = True
        return current_result

    delta = current_overall - baseline_score.overall
    threshold = model_run.prompt_case.suite.regression_threshold
    passed = delta >= -threshold

    current_result.regression_delta = round(delta, 4)
    current_result.passed = passed
    return current_result
