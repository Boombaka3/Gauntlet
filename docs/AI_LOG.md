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
