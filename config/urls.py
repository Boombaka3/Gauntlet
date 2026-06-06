# llm_eval_harness/config/urls.py
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI, Router

from apps.evals.router import router as evals_router

api = NinjaAPI(title="LLM Eval Harness", version="1.0.0", docs_url="/api/docs")

# ── Health check ──────────────────────────────────────────────────────────────
health_router = Router(tags=["health"])


@health_router.get("/health/")
def health(request):
    return {"status": "ok"}


api.add_router("", health_router)
api.add_router("/evals", evals_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", api.urls),
]
