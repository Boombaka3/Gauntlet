# AI_LOG.md — Session Journal

Track what was AI-generated vs manually rewritten each session.

---

## Phase 1 — 2026-06-05

### AI-generated (unmodified)
- `pyproject.toml` — all dependencies, build config, tool settings
- `.env.example` — all required env vars with placeholders
- `docker-compose.yml` — app, postgres, redis, minio services with healthchecks
- `config/settings.py` — django-tenants config, SHARED_APPS/TENANT_APPS split, Celery, S3/MinIO, logging
- `config/urls.py` — NinjaAPI mount, evals router registration
- `config/celery.py` — Celery app init with autodiscover
- `config/wsgi.py` — standard WSGI application
- `apps/core/models.py` — Tenant, Domain (django-tenants mixins)
- `apps/core/admin.py` — TenantAdmin, DomainAdmin
- `apps/users/models.py` — custom User extending AbstractUser, email as USERNAME_FIELD
- `apps/evals/models.py` — EvalSuite, PromptCase, EvalRun, ModelRun, ScoreResult with full status choices
- `scripts/preflight.py` — DB, Redis, MinIO connectivity checks; exits 1 on failure
- `scripts/seed.py` — demo tenant + EvalSuite + 2 PromptCases
- `docs/AI_LOG.md` (this file)
- `docs/architecture.md`
- `docs/interview_prep.md`

### Manually rewritten
- None yet.

---

## Phase 2 — 2026-06-06

### AI-generated (scaffold — review before shipping)
- `apps/evals/models.py` — updated: added `baseline_run` FK to `EvalSuite`
- `apps/evals/schemas.py` — all Pydantic schemas (In/Out/Patch per resource)
- `apps/evals/router.py` — all 13 endpoints; `_get_or_404` helper; `SUPPORTED_MODELS` list
- `apps/evals/adapters/base.py` — `AdapterResult` dataclass, `ModelAdapter` ABC, `from_model_id` factory
- `apps/evals/adapters/anthropic.py` — Anthropic SDK, retry on 429, latency + token_count
- `apps/evals/adapters/openai.py` — OpenAI SDK, `OpenAICompatAdapter` subclass for Ollama/vLLM
- `apps/evals/adapters/gemini.py` — google-generativeai SDK, rate-limit detection via string matching + `ResourceExhausted`
- `apps/evals/scoring/exact_match.py` — difflib ratio ≥ 0.95
- `apps/evals/scoring/rubric.py` — Claude judge call, JSON parse, weighted overall (0–1)
- `apps/evals/scoring/llm_judge.py` — delegates to rubric; fallback single-criterion path
- `apps/evals/scoring/regression.py` — calls llm_judge, diffs against baseline ScoreResult
- `apps/evals/tasks/dispatch.py` — chord fan-out, schema_context propagation
- `apps/evals/tasks/run_model.py` — adapter call, S3 raw output upload, never raises
- `apps/evals/tasks/score.py` — per-mode dispatch, bulk_create, S3 report upload
- `apps/evals/prompts/judge_score.txt` — rubric scoring prompt with escaped JSON shape
- `apps/evals/prompts/judge_regression.txt` — regression comparison prompt
- `config/urls.py` — added health router

### Paths requiring manual review before production
- **Error handling in scoring** — `score_rubric` falls back to `overall=0.0` on any Claude API failure; verify this default is acceptable or surface it as a distinct error state.
- **S3 key construction** — `evals/{schema_name}/{eval_run_id}/{model_run_id}.txt` — confirm bucket policy allows worker IAM role writes.
- **Chord callback** — `score_all_results.si()` ignores `run_model` return values. If a Celery broker restart happens mid-chord, inflight tasks may replay; ensure idempotency (`bulk_create(ignore_conflicts=True)` covers ScoreResult).
- **Gemini rate-limit detection** — string-matching on exception message; replace with explicit `google.api_core.exceptions.ResourceExhausted` catch once confirmed the import is available in your environment.
- **`regression_threshold` default** — currently 0.3 (any drop > 0.3 fails). Tune per suite before enabling regression alerting.

### Manually rewritten
- None yet.

---

## Phase 1.5 -- 2026-06-06

Phase 1.5 -- bin/ restructure and tests/ scaffold. All .ps1 rewritten to fix string terminator bug.

- Moved `start_stack.ps1`, `stop_stack.ps1`, `dev.ps1` from project root into `bin/`
- Root cause of parse error: em dash in UTF-8 encodes as bytes E2 80 94; byte 0x94 is RIGHT DOUBLE QUOTATION MARK in Windows-1252 (PS5.1 default), terminating strings mid-line
- Fix: all strings in .ps1 files now use single quotes or concatenation; zero non-ASCII characters remain
- `$PSScriptRoot` in `bin/` scripts resolves to the `bin/` dir; `Split-Path $PSScriptRoot -Parent` reaches project root
- Created `tests/conftest.py` with `django_db_setup` (session-scoped), `tenant_schema`, and `client` fixtures
- Created `tests/evals/.gitkeep` placeholder

---

## Phase 2.5 -- 2026-06-06

Three runtime bug fixes (all confirmed by audit) + admin registration.

- `tasks/score.py`: `round(overall_avg, 4)` now guards against `None` when all judge calls fail
- `scoring/regression.py`: `delta = current - baseline` guarded against `None` on either side; passes with `delta=None` instead of crashing
- `apps/evals/models.py`: `ScoreResult.__str__` no longer crashes when `self.overall is None`
- `apps/evals/admin.py`: created; registers EvalSuite, PromptCase, EvalRun, ModelRun, ScoreResult

`manage.py check` and `scripts/preflight.py` both pass after these changes.

---

## Phase 2.5 fix — Celery autodiscovery — 2026-06-07

Celery worker started but registered zero app tasks. Root cause was three compounding issues:

- `apps/evals/tasks/__init__.py` was empty (0 bytes) — autodiscovery finds the package but imports nothing, so no `@shared_task` decorator fires
- `autodiscover_tasks(lambda: settings.INSTALLED_APPS)` lambda pattern is unreliable in Celery 5 (deferred signal, not immediate import)
- Without `django.setup()` called before app construction, `django_tenants` fails silently on import, taking the entire tasks module with it

Fix:
- `apps/evals/tasks/__init__.py`: added explicit imports of all three task functions + `__all__`
- `config/celery.py`: added `try: django.setup() except RuntimeError: pass` guard (needed because `config/__init__.py` imports `config/celery.py`, so this module runs during Django's own URL loading when setup is already done); changed to `autodiscover_tasks(["apps.evals"], force=True)` — explicit module list + `force=True` causes immediate import instead of deferred signal

Verification: `uv run celery -A config worker --loglevel=info --pool=solo` confirmed `[tasks]` section shows `evals.dispatch_eval_run`, `evals.run_model`, `evals.score_all_results`.

---

## Phase 4a — Authentication + admin seeding — 2026-06-08

API key auth and superuser bootstrap.

- `apps/users/auth.py`: created `ApiKeyAuth(APIKeyHeader)` — looks up user by api_key in X-API-Key header
- `apps/users/models.py`: added `api_key = CharField(max_length=64, unique=True, blank=True)`; `save()` auto-generates via `secrets.token_urlsafe(32)`
- `apps/users/migrations/0002_add_api_key.py`: migration for api_key field
- `apps/evals/router.py`: imported `ApiKeyAuth`; added `auth=api_key_auth` to all 11 protected endpoints; `/models/` stays public (no auth param)
- `config/urls.py`: auth is per-endpoint only (global NinjaAPI auth skipped — it would block health check); health check remains public
- `scripts/create_admin.py`: created — idempotent superuser + demo tenant seeder; reads DJANGO_SUPERUSER_* env vars; prints API key on completion
- `scripts/first_run.py`: added DJANGO_SUPERUSER_PASSWORD pre-check (exits 1 if missing); added create_admin.py as final step
- `.env.example`: added DJANGO_SUPERUSER_* and GAUNTLET_TENANT_* vars
- `tests/conftest.py`: client fixture now creates testuser in public schema and passes X-API-Key header; all 23 tests pass

---

## Phase 3 fix — smoke_test.py — 2026-06-07

Phase 3 fix — smoke_test.py switched to exact_match for keyless verification;
llm_judge path added as optional skip when no API key present.

- `scripts/smoke_test.py`: score_mode confirmed as "exact_match"; replaced `overall is None` check with `assert res["passed"] is not None` (exact_match sets passed but overall may be 0.0); added `smoke_test_llm_judge()` that skips when ANTHROPIC_API_KEY unset or "placeholder"
- `scripts/first_run.py`: added informational prints after successful first run pointing user to .env and smoke test command

---

## Phase 4d -- Deployment config + portfolio docs -- 2026-06-08

Phase 4d -- railway.toml; .railway.env.example; docs/deployment.md
(Railway fast path + AWS architecture + cost table + shutdown instructions);
README.md with architecture diagram, stack table, quick start, API table,
CV bullets; interview_prep.md updated with 7-step live demo script.

- `railway.toml`: Railway deployment config -- Dockerfile builder, gunicorn start command, /api/health/ healthcheck, ON_FAILURE restart policy
- `.railway.env.example`: all 17 env vars Railway needs with placeholder values
- `docs/deployment.md`: Railway 10-step fast path; AWS local-to-cloud mapping table; cost table (~$60/mo, free first year); shut down instructions for both platforms
- `README.md`: project header, what-it-does, ASCII pipeline architecture, full tech stack table, copy-paste quick start, 13-endpoint API table, test command, deployment pointer, CV bullets
- `docs/interview_prep.md`: added "Live demo script" section -- 7-step walkthrough with Swagger UI through fan-out diagram, covering multi-tenancy, group+chord, partial failure, scoring, and regression tracking

---

## Phase 3 -- 2026-06-07

End-to-end scripts + pytest suite. 23 tests, all passing.

- `scripts/first_run.py`: orchestrates migrate, seed, preflight in sequence
- `scripts/smoke_test.py`: hits live API end-to-end (httpx, Host: demo.localhost)
- `tests/conftest.py`: session-scoped demo tenant creation, tenant_schema, client fixtures
- `tests/evals/conftest.py`: pytestmark = pytest.mark.django_db for all evals tests
- `tests/evals/test_models.py`: 5 tests (suite create, FK constraint, status default, nullable, __str__)
- `tests/evals/test_schemas.py`: 4 tests (valid, missing name, empty models, rubric shape)
- `tests/evals/test_scoring.py`: 6 tests (exact_match x3, regression x3 with mocked llm_judge)
- `tests/evals/test_api.py`: 8 tests (health, CRUD, run, status, regression 400, models list)
- `apps/evals/schemas.py`: added field_validator to EvalRunIn rejecting empty model_ids
- `config/urls.py`: API mounted at api/ (was root); docs_url fixed to /docs
- `scoring/regression.py`: additional round(delta) None guard (follow-on to Phase 2.5 fix)
- `pyproject.toml`: pytest addopts, python_classes/functions, markers added

---
