# Interview Prep — LLM Eval Harness

---

## Multi-tenancy

We use `django-tenants` with a schema-per-tenant strategy on PostgreSQL. Every customer team gets a dedicated PostgreSQL schema (e.g., `acme`, `demo`) that contains their own copies of the `evals_*` tables. The PUBLIC schema holds only cross-cutting concerns: `Tenant`, `Domain`, and `User`. The Django ORM routes queries automatically — after the request middleware resolves the hostname to a `Tenant` row and calls `set_schema()`, every subsequent ORM query targets that tenant's schema. This means there is no application-level `WHERE tenant_id = ?` filtering; isolation is enforced by the database itself.

---

## Fan-out pattern

When a new `EvalRun` is created via the API, `dispatch_eval_run` is called as a Celery task. It iterates every `PromptCase` in the suite and every `model_id` in the run, creates a `ModelRun` row for each combination (N cases × M models), then builds a Celery `group` of `run_model.si(model_run_id)` signatures — one per `ModelRun`. The group is wrapped in a `chord`: all `run_model` tasks execute in parallel, and only after every task in the group has completed (success or failure) does the chord callback, `score_all_results.si(eval_run_id)`, fire. This guarantees we have a complete picture of all model outputs before scoring begins.

---

## Partial failure

`run_model` is designed to never raise. It wraps the adapter call and the S3 upload in a broad `try/except`, and in the except block it writes the error message to `ModelRun.error_message` and sets `ModelRun.status = FAILED` before returning. Because Celery `group` tracks completion by task termination rather than success, a failed `run_model` task still counts as "done" for the chord, so `score_all_results` fires regardless. The scoring task then simply skips `ModelRun` rows whose status is `FAILED`, writing `ScoreResult` only for successful outputs. The final report includes both succeeded and failed runs so the caller can see the partial results.

---

## LLM-as-judge

For `rubric` and `llm_judge` score modes, we call the Claude API with a structured prompt loaded at runtime from `apps/evals/prompts/judge_score.txt`. The prompt injects the original system prompt, user prompt, model output, and the suite's rubric criteria list. Claude is instructed to return a JSON object of the form `{criterion: score (1–5), reasoning: str}`. We parse that JSON, compute a weighted average using the criterion weights stored in `EvalSuite.rubric`, and store the result in `ScoreResult.scores` (per-criterion) and `ScoreResult.overall` (weighted float). The raw reasoning string is preserved in `ScoreResult.judge_reasoning` for auditability.

---

## Regression tracking

Any `EvalRun` can be pinned as a baseline by calling `POST /runs/{id}/pin-baseline/`, which writes the run's `id` to `EvalSuite.baseline_run_id`. When a new run is created with `score_mode=regression`, `score_all_results` looks up the `ScoreResult` for the same (`PromptCase`, `model_id`) pair from the baseline run and computes `regression_delta = current.overall - baseline.overall`. A negative delta means the model got worse. The run is marked `passed = False` if `regression_delta < -threshold`, where `threshold` defaults to `0.3` but is configurable per `EvalSuite`. This value and the delta are stored on `ScoreResult` so you can sort, filter, and alert on regressions from the API or a dashboard.

---

## S3 / presigned URL pattern

Raw model outputs and final JSON reports are stored in MinIO (S3-compatible) rather than in the database. After `run_model` receives a response, it uploads the raw text to `s3://{bucket}/{eval_run_id}/{model_run_id}.txt` using a standard `put_object` call and stores the resulting key in `ModelRun.s3_key`. If a client needs to download the raw output, the API generates a presigned URL via `boto3.generate_presigned_url` and returns only that URL — the server never reads the bytes back and proxies them. This keeps database rows small and means large outputs (code, long documents) do not impact API response times.

---

## Model adapter pattern

All four provider adapters (`AnthropicAdapter`, `OpenAIAdapter`, `GeminiAdapter`, `OpenAICompatAdapter`) implement the same `ModelAdapter` abstract base class with a single `complete(system_prompt, user_prompt, max_tokens, timeout) -> AdapterResult` method. The factory classmethod `ModelAdapter.from_model_id(model_id)` routes by prefix: `claude-*` → Anthropic, `gpt-*` / `o1*` → OpenAI, `gemini-*` → Gemini, anything else → the OpenAI-compatible adapter pointed at `OPENAI_COMPAT_BASE_URL` (Ollama, vLLM, etc.). Adding a new provider means creating one new file in `adapters/` and adding a new prefix branch in the factory — zero changes elsewhere in the codebase.

---

## Django Ninja vs DRF

Django REST Framework relies on class-based `Serializer` and `ViewSet` abstractions that duplicate model declarations and require manual wiring. Django Ninja is Pydantic-native: request bodies and responses are typed with Pydantic models defined in `schemas.py`, validated automatically, and serialized to JSON without any serializer class. It also generates an OpenAPI schema for free. For this project the schemas are co-located with the router in `apps/evals/`, making it easy to see the contract for every endpoint in one place. Ninja also supports `async def` view functions natively, which matters when we want to add async scoring paths without switching frameworks.

---

## Live demo script

Step-by-step walkthrough for an interview setting.

**1. Open http://localhost:8000/api/docs**

Say: "This is the Swagger UI auto-generated by Django Ninja from the API schemas. Every request and response type is defined in `apps/evals/schemas.py` using Pydantic — no separate serializer classes."

**2. POST /api/evals/suites/ -- fill in name, version, rubric criteria**

Say: "Each tenant has isolated data -- this suite is only visible in the demo schema. The middleware resolves the `Host` header to a tenant row and sets the PostgreSQL schema before any ORM query runs."

**3. POST /api/evals/suites/{id}/cases/ -- add two prompt cases with expected outputs**

Say: "Each case is a (system_prompt, user_prompt, expected_output) triple. You can tag cases for filtering. The suite's rubric criteria and weights live on the suite, not the case."

**4. POST /api/evals/runs/ -- select two models, set score_mode=exact_match**

Say: "Dispatching creates N x M Celery tasks -- one per prompt-case/model pair -- all running in parallel via group + chord. With 2 cases and 2 models that's 4 parallel tasks. The chord callback only fires after all 4 complete, whether they succeed or fail."

**5. Poll GET /api/evals/runs/{id}/ -- show PENDING -> RUNNING -> DONE live**

Say: "The chord callback fires score_all_results only after every model task completes -- including failed ones, which are scored with empty output. Progress is tracked by counting DONE + FAILED ModelRun rows against total."

**6. GET /api/evals/runs/{id}/results/ -- show scored outputs table**

Say: "ScoreResults store per-criterion rubric scores, overall, passed, and regression_delta against any pinned baseline run. For exact_match, overall is a difflib ratio and passed is true when it exceeds 0.95."

**7. Draw the ASCII pipeline on a whiteboard from memory**

```
POST /api/evals/runs/
  -> EvalRun created
  -> Celery group: N x M run_model tasks (parallel)
      -> Claude / GPT-4o / Gemini adapters
      -> raw output stored to S3 + DB
  -> chord: score_all_results when all done
      -> exact_match / rubric / llm_judge / regression scoring
      -> ScoreResult written per ModelRun
      -> report JSON uploaded to S3
      -> EvalRun marked DONE
```

Say: "The fan-out is the interesting distributed systems problem -- 30 tasks in parallel, one chord callback, partial failure handled at the task level. The chord only fires once; if the broker restarts mid-run, ScoreResult uses `ignore_conflicts=True` on bulk_create so re-scoring is idempotent."
