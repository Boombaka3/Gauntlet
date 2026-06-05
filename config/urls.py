# llm_eval_harness/config/urls.py
from django.contrib import admin
from django.urls import path
from ninja import NinjaAPI

from apps.evals.router import router as evals_router

api = NinjaAPI(title="LLM Eval Harness", version="1.0.0", docs_url="/api/docs")
api.add_router("/evals", evals_router)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", api.urls),
]
