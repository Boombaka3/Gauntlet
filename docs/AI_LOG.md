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

## FE-1 through FE-4 -- React dashboard -- 2026-06-09

Full React 19 + Vite + Tailwind frontend, built and served from Django.

- `frontend/package.json`: React 19, react-router-dom 6, recharts, Vite 5, Tailwind v3
- `frontend/vite.config.js`: functional config -- `base: '/static/frontend/'` in production, `/` in dev; build to `../staticfiles/frontend`; proxy `/api` to Django with `Host: demo.localhost`
- `frontend/src/api/client.js`: 14 named async functions covering all backend endpoints; reads `VITE_API_KEY` + `VITE_API_BASE` from env; throws `Error` with backend message on non-2xx
- `frontend/src/components/Layout.jsx`: 240px fixed sidebar, Gauntlet brand, NavLink active state indigo-500
- `frontend/src/components/StatusBadge.jsx`: pill with color by status (PENDING/DISPATCHED/RUNNING/DONE/FAILED); RUNNING animates-pulse
- `frontend/src/components/ProgressBar.jsx`: current/total label + indigo fill bar
- `frontend/src/components/ScoreBar.jsx`: green/amber/red by threshold (0.8/0.5), null → "N/A"
- `frontend/src/components/ModelCompare.jsx`: sorted table (best first) with regression delta coloring
- `frontend/src/pages/Suites.jsx`: list + inline create form with dynamic rubric criteria rows
- `frontend/src/pages/Cases.jsx`: list + inline add form + delete with confirm; "Run this suite" to /runs/new?suite_id
- `frontend/src/pages/NewRun.jsx`: suite select (pre-filled from query param), model checkboxes, score mode radio, baseline run ID, dispatch → /runs/{id}
- `frontend/src/pages/Runs.jsx`: placeholder with New Run CTA (no list endpoint on backend yet)
- `frontend/src/pages/RunStatus.jsx`: polls every 3s via setInterval; stops on DONE/FAILED; cleanup on unmount; pulsing dot indicator
- `frontend/src/pages/Results.jsx`: 4 stat boxes + ModelCompare + full results table + regression section
- `config/settings.py`: added `corsheaders` to SHARED_APPS; CorsMiddleware first in MIDDLEWARE; CORS_ALLOWED_ORIGINS from env; TEMPLATES DIRS includes `staticfiles/frontend`
- `config/urls.py`: added `re_path(r'^(?!api/).*$', TemplateView)` catch-all for React Router
- `docker-entrypoint.sh`: created -- frontend npm build → migrate → collectstatic → create_admin → exec
- `Dockerfile`: added Node.js via apt-get; COPY frontend/; ENTRYPOINT docker-entrypoint.sh
- `bin/dev.ps1`: added Step 4 -- Vite dev server window; updated URLs printed
- `pyproject.toml`: added django-cors-headers>=4.3.0
- Build verified: `npm run build` → `staticfiles/frontend/index.html` references `/static/frontend/assets/...` (correct for Whitenoise)
- `manage.py check`: 0 issues; `collectstatic`: 127 files

End-to-end test: backend was not running in CI environment; test manually with `bin/dev.ps1` then open http://localhost:5173 (dev) or http://localhost:8000 (production build).

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


---

## FE-1 redesign + FE-2 + FE-3 + FE-4 -- Gauntlet design system -- 2026-06-10

Complete frontend redesign with gauntlet design system and useApi hook with mock data fallback.

- `frontend/tailwind.config.js`: added `gauntlet` color token namespace (bg/surface/border/accent/success/warning/danger/muted/text); added Inter + JetBrains Mono to fontFamily
- `frontend/index.html`: Google Fonts import for Inter:400,500,600 + JetBrains Mono:400,500; title "Gauntlet"
- `frontend/src/index.css`: body bg-gauntlet-bg + text-gauntlet-text + font Inter
- `frontend/vite.config.js`: manualChunks (vendor + charts); unchanged otherwise
- `frontend/src/hooks/useApi.js`: created -- wraps apiFn with loading/error/isMock states; falls back to mockData on error; tick counter enables refetch()
- `frontend/src/data/mockData.js`: created -- MOCK_SUITES/MOCK_CASES/MOCK_RUNS/MOCK_RESULTS/MOCK_MODELS with realistic sample data
- `frontend/src/components/MockBanner.jsx`: created -- amber warning bar with pulsing dot; shown when isMock=true
- `frontend/src/components/ApiStatus.jsx`: created -- polls /api/health/ every 30s; fixed bottom bar; green=connected, red pulsing=offline
- `frontend/src/components/ErrorState.jsx`: created -- centered error with optional retry button
- `frontend/src/components/LoadingState.jsx`: created -- N skeleton rows with animate-pulse
- `frontend/src/components/StatusBadge.jsx`: rewritten -- gauntlet tokens; RUNNING animate-pulse; size prop (sm/lg)
- `frontend/src/components/Sidebar.jsx`: created -- 240px fixed; brand + nav with SVG icons; active state border-l-2 accent
- `frontend/src/components/Layout.jsx`: rewritten -- uses Sidebar + ApiStatus; pb-8 for status bar
- `frontend/src/components/ProgressBar.jsx`: created -- current/total label + accent fill with transition-all duration-500
- `frontend/src/components/ScoreBar.jsx`: created -- color by threshold ≥0.8=success ≥0.5=warning <0.5=danger; null → N/A
- `frontend/src/components/DeltaBadge.jsx`: created -- +/- with success/danger/muted; null → "--"
- `frontend/src/components/ModelCompare.jsx`: created -- sorted table descending; uses ScoreBar + DeltaBadge
- `frontend/src/api/client.js`: rewritten -- removed X-API-Key header entirely; simplified to one-liner exports
- `frontend/src/pages/Suites.jsx`: rewritten with useApi + MOCK_SUITES; gauntlet tokens; dynamic rubric create form
- `frontend/src/pages/Cases.jsx`: rewritten with useApi + MOCK_CASES; gauntlet tokens; inline add/delete
- `frontend/src/pages/NewRun.jsx`: rewritten with useApi + MOCK_SUITES + MOCK_MODELS; score mode as radio CARDS; gauntlet tokens
- `frontend/src/pages/Runs.jsx`: rewritten -- info box with gauntlet tokens; New Run CTA
- `frontend/src/pages/RunStatus.jsx`: rewritten -- manual interval polling (no useApi); MOCK_RUNS fallback; duration calculation; gauntlet tokens
- `frontend/src/pages/Results.jsx`: rewritten with useApi + MOCK_RESULTS; 4 stat cards; ModelCompare; grouped by case; regression summary
- `frontend/src/App.jsx`: updated -- models route now uses gauntlet inline placeholder
- `config/urls.py`: catch-all regex updated to also exclude /admin/ and /static/
- Build verified: `npm run build` → 57 modules, 6 output files, 0 errors
- Dev server verified: starts cleanly on localhost:5175 (5173/5174 in use from other processes)

---

## EvidenceTrace migration — 2026-06-10

Gauntlet upgraded to biomedical claim conflict detection pipeline. apps/evals → apps/evidence. New models: Paper, Claim, ConflictPair, RewardScore, AnalysisJob. New tasks: extract_claims, build_conflict_graph, dispatch. Level 1 RL: consistency reward voting across N samples. Prompt files replaced for claim extraction and conflict judgment.

- Branch: evidencetrace (created from main)
- `pyproject.toml`: name=evidence-trace, description updated, added pdfplumber>=0.11.0, sentence-transformers>=3.0.0, torch>=2.0.0
- `bin/dev.ps1`, `bin/start_stack.ps1`: banner changed from "LLM Eval Harness" to "EvidenceTrace"
- `config/settings.py`: TENANT_APPS apps.evals → apps.evidence
- `config/celery.py`: Celery app name "evidence_trace", autodiscover apps.evidence
- `config/urls.py`: api prefix /api/evals/ → /api/evidence/, import from apps.evidence.router
- `apps/evidence/__init__.py`: new app
- `apps/evidence/models.py`: 5 models — AnalysisJob, Paper, Claim, ConflictPair, RewardScore; TenantModel alias for models.Model
- `apps/evidence/admin.py`: admin for all 5 models
- `apps/evidence/schemas.py`: JobIn/Out, PaperOut, ClaimOut, ConflictPairOut, RewardScoreOut, ReportOut
- `apps/evidence/router.py`: 8 endpoints — POST/GET jobs, POST/GET papers (multipart PDF upload → S3), POST dispatch, GET claims, GET conflicts, GET report
- `apps/evidence/adapters/base.py`: AdapterResult + ModelAdapter.for_claude() factory
- `apps/evidence/adapters/anthropic.py`: AnthropicAdapter (retry on rate limit)
- `apps/evidence/prompts/claim_extractor.txt`: JSON claim extraction prompt
- `apps/evidence/prompts/conflict_judge.txt`: JSON conflict judgment prompt
- `apps/evidence/utils/pdf_parser.py`: pdfplumber section extractor (body/abstract/methods/results/discussion sections)
- `apps/evidence/scoring/conflict_judge.py`: judge_conflict(claim_a, claim_b) → unsaved ConflictPair
- `apps/evidence/scoring/reward_voting.py`: compute_reward(conflict_pair_id, n_samples) → unsaved RewardScore; consistency = majority_count / n_samples
- `apps/evidence/tasks/extract_claims.py`: @shared_task; reads PDF from S3, extract_sections, Claude per section, create Claim rows
- `apps/evidence/tasks/build_graph.py`: @shared_task; cross-paper claim pairs → judge_conflict → RewardScore → mark job DONE
- `apps/evidence/tasks/dispatch.py`: @shared_task; Celery chord — group(extract_claims) | build_conflict_graph
- `apps/evidence/migrations/0001_initial.py`: auto-generated by makemigrations evidence
- `scripts/smoke_test.py`: new flow — create job, upload 2 synthetic PDFs, dispatch, poll until DONE, assert conflicts
- Verified: makemigrations evidence → 0001_initial.py; manage.py check → 0 issues; migrate_schemas --shared → OK

---

## EvidenceTrace Phase 4a migration complete — 2026-06-11

EvidenceTrace migration complete. Gauntlet → EvidenceTrace on branch
evidencetrace. apps/evals → apps/evidence. New models: Paper, Claim,
ConflictPair, RewardScore, AnalysisJob. New tasks: extract_claims (PDF →
Claude → Claim objects), build_conflict_graph (pairwise conflict detection
+ Level 1 RL consistency voting), dispatch (group+chord fan-out).
Prompt files: claim_extractor.txt + conflict_judge.txt. Admin registered.
Smoke test updated for EvidenceTrace pipeline.

---

## NaviGator Toolkit integration — 2026-06-13

Replaced all direct Anthropic Claude API calls with the UF NaviGator Toolkit
(OpenAI-compatible API at https://api.ai.it.ufl.edu/v1). All models run locally
on HiPerGator — no external API costs.

- `apps/evidence/adapters/openai.py`: new `OpenAICompatAdapter` class; reads
  `OPENAI_COMPAT_BASE_URL`, `OPENAI_API_KEY`, `NAVIGATOR_MODEL` env vars;
  uses `openai.OpenAI(base_url=...)` client; retry on RateLimitError; returns `AdapterResult`
- `scoring/conflict_judge.py`: removed `import anthropic`; `_call_claude()` replaced by
  `_call_judge()` via `_get_adapter()`; fallback returns `{}` on adapter error
- `scoring/faithfulness.py`: removed `import anthropic`; inline `OpenAICompatAdapter` call,
  `max_tokens=256`; explicit error dict returned on `result.error`
- `tasks/extract_claims.py`: removed `import anthropic`; adapter instantiated once per task
  before section loop; `result.error` logged and section skipped via `continue`
- `scripts/test_navigator.py`: new connection test — sends minimal conflict prompt,
  verifies JSON verdict returned; exit 1 if key missing or response unparseable
- `scripts/smoke_test.py`: added `dotenv.load_dotenv()`; `ANTHROPIC_KEY` → `NAVIGATOR_KEY`
  checking `OPENAI_API_KEY`; updated warning message to mention NaviGator
- `scripts/benchmark.py`: `ANTHROPIC_API_KEY` guard replaced with `OPENAI_API_KEY`
  guard; error message directs user to set `OPENAI_COMPAT_BASE_URL` and NaviGator key
- `.env.example`: `OPENAI_COMPAT_BASE_URL=https://api.ai.it.ufl.edu/v1`,
  `OPENAI_API_KEY=<your-navigator-api-key>`, `NAVIGATOR_MODEL=llama-3.3-70b-instruct`

Default model: `llama-3.3-70b-instruct`. Medical alternative: `medgemma-27b-it`.
Switch via `NAVIGATOR_MODEL` env var — no code changes required.

manage.py check: 0 issues. Committed and pushed to evidencetrace.
