# llm_eval_harness/apps/evals/schemas.py
from datetime import datetime

from ninja import Schema
from pydantic import ConfigDict


# ── EvalSuite ─────────────────────────────────────────────────────────────────

class EvalSuiteIn(Schema):
    name: str
    version: int = 1
    description: str = ""
    rubric: list[dict] = []
    regression_threshold: float = 0.3


class EvalSuitePatch(Schema):
    name: str | None = None
    version: int | None = None
    description: str | None = None
    rubric: list[dict] | None = None
    regression_threshold: float | None = None


class EvalSuiteOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    version: int
    description: str
    rubric: list[dict]
    regression_threshold: float
    baseline_run_id: int | None
    created_at: datetime
    updated_at: datetime


# ── PromptCase ────────────────────────────────────────────────────────────────

class PromptCaseIn(Schema):
    name: str
    system_prompt: str
    user_prompt: str
    expected_output: str | None = None
    tags: list[str] = []


class PromptCaseOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    suite_id: int
    name: str
    system_prompt: str
    user_prompt: str
    expected_output: str | None
    tags: list
    created_at: datetime


# ── EvalRun ───────────────────────────────────────────────────────────────────

class EvalRunIn(Schema):
    suite_id: int
    model_ids: list[str]
    score_mode: str = "llm_judge"
    baseline_run_id: int | None = None


class EvalRunOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    suite_id: int
    status: str
    model_ids: list
    score_mode: str
    baseline_run_id: int | None
    progress: int
    total: int
    started_at: datetime | None
    finished_at: datetime | None
    result_s3_key: str | None
    created_at: datetime


# ── RunStatus (lightweight) ───────────────────────────────────────────────────

class RunStatusOut(Schema):
    id: int
    status: str
    progress: int
    total: int
    score_mode: str
    started_at: datetime | None
    finished_at: datetime | None


# ── ModelRun ──────────────────────────────────────────────────────────────────

class ModelRunOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    eval_run_id: int
    prompt_case_id: int
    model_id: str
    status: str
    raw_output: str
    latency_ms: int | None
    token_count: int | None
    error_message: str | None
    s3_key: str | None
    created_at: datetime


# ── ScoreResult ───────────────────────────────────────────────────────────────

class ScoreResultOut(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    model_run_id: int
    scores: dict
    overall: float | None
    passed: bool | None
    judge_reasoning: str | None
    regression_delta: float | None
    created_at: datetime


# ── Regression report ─────────────────────────────────────────────────────────

class RegressionItem(Schema):
    prompt_case_id: int
    model_id: str
    delta: float | None
    passed: bool


class RegressionReportOut(Schema):
    run_id: int
    baseline_run_id: int
    items: list[RegressionItem]
