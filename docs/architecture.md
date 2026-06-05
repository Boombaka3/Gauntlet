# Architecture

## config/
Django project configuration layer. `settings.py` reads all secrets from environment variables via python-dotenv and configures django-tenants (SHARED_APPS / TENANT_APPS split), Celery broker/backend pointing at Redis, and boto3 credentials for S3-compatible MinIO storage. `celery.py` initialises the Celery application and autodiscovers tasks from all installed apps. `urls.py` mounts a single Django Ninja `NinjaAPI` instance at the root and registers the evals router under `/api/evals/`.

## apps/core/
Lives in the PUBLIC PostgreSQL schema. Defines `Tenant` (one row per customer team, owns a dedicated schema) and `Domain` (maps hostnames to tenants) using the `django-tenants` mixins. The admin registers both models so operators can provision new tenants through Django Admin without writing SQL.

## apps/users/
Lives in the PUBLIC schema. Provides a custom `User` model that swaps `email` for `username` as the login field while keeping all standard Django auth behaviour (groups, permissions, sessions). Keeping auth in the public schema means a single user account can be associated with multiple tenant schemas without duplication.

## apps/evals/
The core business logic — lives entirely in each TENANT schema so every team's data is fully isolated at the database level. Contains five models: `EvalSuite` (named, versioned collection of prompt cases with a rubric and regression threshold), `PromptCase` (individual system+user prompt pair with an optional expected output), `EvalRun` (a single execution of a suite against N models, tracks status and score mode), `ModelRun` (one LLM call — one PromptCase × one model\_id — stores raw output, latency, token count, and S3 key), and `ScoreResult` (the scored outcome of a ModelRun, including per-criterion scores, overall float, pass/fail, and optional regression delta).

## apps/evals/tasks/
Celery task graph implementing the fan-out pattern. `dispatch.py` creates one `ModelRun` row per (PromptCase × model) combination, builds a Celery `group` of `run_model` tasks, and wraps them in a `chord` so `score_all_results` fires only after every model output has been collected. `run_model.py` selects the correct adapter by model\_id prefix, calls `adapter.complete()`, saves output to DB and S3, and always updates ModelRun status — even on failure. `score.py` iterates all ModelRuns for the run, applies the configured scoring mode, writes one `ScoreResult` per run, assembles a JSON report, uploads it to S3, and marks the EvalRun DONE.

## apps/evals/adapters/
Thin, uniform wrappers around each LLM provider SDK. `base.py` defines the `ModelAdapter` abstract class with a `complete()` method and a `from_model_id()` factory that routes by prefix (`claude-` → Anthropic, `gpt-`/`o1` → OpenAI, `gemini-` → Gemini, anything else → OpenAI-compatible). Each concrete adapter handles timeout, single retry with exponential backoff on rate-limit responses, and returns an `AdapterResult` dataclass — never raises.

## apps/evals/scoring/
Four scoring strategies behind a common function signature. `exact_match.py` uses `difflib.SequenceMatcher` (ratio ≥ 0.95 → pass). `rubric.py` and `llm_judge.py` both delegate to the Claude API using the `judge_score.txt` prompt template, parsing the JSON response into per-criterion scores and a weighted overall. `regression.py` looks up the corresponding `ScoreResult` from the pinned baseline run and computes `regression_delta = current.overall - baseline.overall`, marking passed if the delta is above `-threshold`.

## apps/evals/prompts/
Plain-text Jinja-style prompt templates loaded at runtime with `open()`. `judge_score.txt` instructs Claude to act as an objective evaluator and return a JSON object mapping each rubric criterion to a score (1–5) plus a `reasoning` string. `judge_regression.txt` is a variant that includes baseline output alongside current output for comparative regression analysis.

## scripts/
`preflight.py` is executed before the app server starts; it checks DB connectivity, Redis `PING`, and MinIO bucket existence, exiting with code 1 on any failure so orchestrators can restart the container cleanly. `seed.py` is a one-time idempotent script that provisions the `demo` tenant schema and populates it with a sample `EvalSuite` and two `PromptCase` rows for smoke-testing the harness end-to-end.
