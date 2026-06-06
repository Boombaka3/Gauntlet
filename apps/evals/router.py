# llm_eval_harness/apps/evals/router.py
import logging

from django.db import connection
from ninja import Router
from ninja.errors import HttpError

from apps.evals.models import EvalRun, EvalSuite, ModelRun, PromptCase, ScoreResult
from apps.evals.schemas import (
    EvalRunIn,
    EvalRunOut,
    EvalSuiteIn,
    EvalSuiteOut,
    EvalSuitePatch,
    ModelRunOut,
    PromptCaseIn,
    PromptCaseOut,
    RegressionItem,
    RegressionReportOut,
    RunStatusOut,
    ScoreResultOut,
)

logger = logging.getLogger(__name__)
router = Router(tags=["evals"])

SUPPORTED_MODELS: list[str] = [
    # Anthropic
    "claude-opus-4-8",
    "claude-sonnet-4-6",
    "claude-haiku-4-5-20251001",
    # OpenAI
    "gpt-4o",
    "gpt-4o-mini",
    "gpt-4-turbo",
    "o1-preview",
    "o1-mini",
    "o3-mini",
    # Gemini
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "gemini-2.0-flash",
    # OpenAI-compatible (Ollama / vLLM examples)
    "ollama/llama3",
    "ollama/mistral",
    "ollama/codellama",
]


# ── EvalSuite endpoints ───────────────────────────────────────────────────────

@router.post("/suites/", response=EvalSuiteOut)
def create_suite(request, data: EvalSuiteIn):
    suite = EvalSuite.objects.create(
        name=data.name,
        version=data.version,
        description=data.description,
        rubric=data.rubric,
        regression_threshold=data.regression_threshold,
    )
    return _suite_out(suite)


@router.get("/suites/", response=list[EvalSuiteOut])
def list_suites(request):
    return [_suite_out(s) for s in EvalSuite.objects.all()]


@router.get("/suites/{suite_id}/", response=EvalSuiteOut)
def get_suite(request, suite_id: int):
    suite = _get_or_404(EvalSuite, suite_id)
    return _suite_out(suite)


@router.patch("/suites/{suite_id}/", response=EvalSuiteOut)
def patch_suite(request, suite_id: int, data: EvalSuitePatch):
    suite = _get_or_404(EvalSuite, suite_id)
    fields_changed = []
    if data.name is not None:
        suite.name = data.name
        fields_changed.append("name")
    if data.version is not None:
        suite.version = data.version
        fields_changed.append("version")
    if data.description is not None:
        suite.description = data.description
        fields_changed.append("description")
    if data.rubric is not None:
        suite.rubric = data.rubric
        fields_changed.append("rubric")
    if data.regression_threshold is not None:
        suite.regression_threshold = data.regression_threshold
        fields_changed.append("regression_threshold")
    if fields_changed:
        suite.save(update_fields=fields_changed + ["updated_at"])
    return _suite_out(suite)


# ── PromptCase endpoints ──────────────────────────────────────────────────────

@router.post("/suites/{suite_id}/cases/", response=PromptCaseOut)
def create_case(request, suite_id: int, data: PromptCaseIn):
    suite = _get_or_404(EvalSuite, suite_id)
    case = PromptCase.objects.create(
        suite=suite,
        name=data.name,
        system_prompt=data.system_prompt,
        user_prompt=data.user_prompt,
        expected_output=data.expected_output,
        tags=data.tags,
    )
    return _case_out(case)


@router.get("/suites/{suite_id}/cases/", response=list[PromptCaseOut])
def list_cases(request, suite_id: int):
    suite = _get_or_404(EvalSuite, suite_id)
    return [_case_out(c) for c in suite.cases.all()]


@router.delete("/cases/{case_id}/")
def delete_case(request, case_id: int):
    case = _get_or_404(PromptCase, case_id)
    case.delete()
    return {"deleted": True}


# ── EvalRun endpoints ─────────────────────────────────────────────────────────

@router.post("/runs/", response=EvalRunOut)
def create_run(request, data: EvalRunIn):
    suite = _get_or_404(EvalSuite, data.suite_id)

    if data.score_mode == EvalRun.ScoreMode.REGRESSION and data.baseline_run_id is None:
        if suite.baseline_run_id is None:
            raise HttpError(
                400,
                "score_mode=regression requires a baseline run. "
                "Pin one with POST /runs/{id}/pin-baseline/ first.",
            )
        baseline_run_id = suite.baseline_run_id
    else:
        baseline_run_id = data.baseline_run_id

    eval_run = EvalRun.objects.create(
        suite=suite,
        models=data.models,
        score_mode=data.score_mode,
        baseline_run_id=baseline_run_id,
        status=EvalRun.Status.PENDING,
    )

    from apps.evals.tasks.dispatch import dispatch_eval_run
    schema_name = connection.schema_name
    dispatch_eval_run.delay(eval_run.id, schema_name)

    return _run_out(eval_run)


@router.get("/runs/{run_id}/", response=RunStatusOut)
def get_run_status(request, run_id: int):
    eval_run = _get_or_404(EvalRun, run_id)
    total = eval_run.model_runs.count()
    progress = eval_run.model_runs.filter(
        status__in=[ModelRun.Status.DONE, ModelRun.Status.FAILED]
    ).count()
    return RunStatusOut(
        id=eval_run.id,
        status=eval_run.status,
        progress=progress,
        total=total,
        score_mode=eval_run.score_mode,
        started_at=eval_run.started_at,
        finished_at=eval_run.finished_at,
    )


@router.get("/runs/{run_id}/results/", response=list[ScoreResultOut])
def get_run_results(request, run_id: int):
    eval_run = _get_or_404(EvalRun, run_id)
    results = (
        ScoreResult.objects
        .filter(model_run__eval_run=eval_run)
        .select_related("model_run")
        .order_by("model_run__created_at")
    )
    return [_score_out(sr) for sr in results]


@router.get("/runs/{run_id}/regression/", response=RegressionReportOut)
def get_regression_report(request, run_id: int):
    eval_run = _get_or_404(EvalRun, run_id)
    if not eval_run.baseline_run_id:
        raise HttpError(400, "This EvalRun has no baseline_run set; cannot produce regression report")

    results = (
        ScoreResult.objects
        .filter(model_run__eval_run=eval_run)
        .select_related("model_run", "model_run__prompt_case")
    )
    items = [
        RegressionItem(
            prompt_case_id=sr.model_run.prompt_case_id,
            model_id=sr.model_run.model_id,
            delta=sr.regression_delta,
            passed=sr.passed,
        )
        for sr in results
    ]
    return RegressionReportOut(
        run_id=eval_run.id,
        baseline_run_id=eval_run.baseline_run_id,
        items=items,
    )


@router.post("/runs/{run_id}/pin-baseline/")
def pin_baseline(request, run_id: int):
    eval_run = _get_or_404(EvalRun, run_id)
    suite = eval_run.suite
    suite.baseline_run = eval_run
    suite.save(update_fields=["baseline_run", "updated_at"])
    logger.info("EvalRun %s pinned as baseline for suite %s", run_id, suite.id)
    return {"status": "pinned", "baseline_run_id": run_id, "suite_id": suite.id}


# ── Models list ───────────────────────────────────────────────────────────────

@router.get("/models/", response=list[str])
def list_models(request):
    return SUPPORTED_MODELS


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_or_404(model_class, pk: int):
    obj = model_class.objects.filter(pk=pk).first()
    if obj is None:
        raise HttpError(404, f"{model_class.__name__} {pk} not found")
    return obj


def _suite_out(suite: EvalSuite) -> dict:
    return {
        "id": suite.id,
        "name": suite.name,
        "version": suite.version,
        "description": suite.description,
        "rubric": suite.rubric,
        "regression_threshold": suite.regression_threshold,
        "baseline_run_id": suite.baseline_run_id,
        "created_at": suite.created_at,
        "updated_at": suite.updated_at,
    }


def _case_out(case: PromptCase) -> dict:
    return {
        "id": case.id,
        "suite_id": case.suite_id,
        "name": case.name,
        "system_prompt": case.system_prompt,
        "user_prompt": case.user_prompt,
        "expected_output": case.expected_output,
        "tags": case.tags,
        "created_at": case.created_at,
    }


def _run_out(eval_run: EvalRun) -> dict:
    total = eval_run.model_runs.count()
    progress = eval_run.model_runs.filter(
        status__in=[ModelRun.Status.DONE, ModelRun.Status.FAILED]
    ).count()
    return {
        "id": eval_run.id,
        "suite_id": eval_run.suite_id,
        "status": eval_run.status,
        "models": eval_run.models,
        "score_mode": eval_run.score_mode,
        "baseline_run_id": eval_run.baseline_run_id,
        "progress": progress,
        "total": total,
        "started_at": eval_run.started_at,
        "finished_at": eval_run.finished_at,
        "result_s3_key": eval_run.result_s3_key,
        "created_at": eval_run.created_at,
    }


def _score_out(sr: ScoreResult) -> dict:
    return {
        "id": sr.id,
        "model_run_id": sr.model_run_id,
        "scores": sr.scores,
        "overall": sr.overall,
        "passed": sr.passed,
        "judge_reasoning": sr.judge_reasoning,
        "regression_delta": sr.regression_delta,
        "created_at": sr.created_at,
    }
