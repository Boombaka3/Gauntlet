# llm_eval_harness/apps/evals/scoring/exact_match.py
import difflib

from apps.evals.models import ModelRun, ScoreResult

PASS_THRESHOLD = 0.95


def score_exact_match(model_run: ModelRun) -> ScoreResult:
    """
    Returns an UNSAVED ScoreResult.
    If no expected_output: scores={"exact": None}, passed=True, overall=1.0.
    Otherwise uses difflib ratio; passed when ratio >= 0.95.
    """
    expected = model_run.prompt_case.expected_output

    if expected is None:
        return ScoreResult(
            model_run=model_run,
            scores={"exact": None},
            overall=1.0,
            passed=True,
        )

    ratio = difflib.SequenceMatcher(
        None,
        model_run.raw_output.strip(),
        expected.strip(),
    ).ratio()

    passed = ratio >= PASS_THRESHOLD
    return ScoreResult(
        model_run=model_run,
        scores={"exact": round(ratio, 4)},
        overall=round(ratio, 4),
        passed=passed,
    )
