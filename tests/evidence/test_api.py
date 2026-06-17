# tests/evidence/test_api.py
import json

import pytest
from django.test import Client
from django_tenants.utils import schema_context
from unittest.mock import patch

pytestmark = pytest.mark.django_db


def _client(api_key):
    return Client(HTTP_HOST="demo.localhost", HTTP_X_API_KEY=api_key)


def _post_json(c, path, body):
    return c.post(path, data=json.dumps(body), content_type="application/json")


# ── Health ─────────────────────────────────────────────────────────────────────

def test_health_check():
    c = Client(HTTP_HOST="demo.localhost")
    res = c.get("/api/health/")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


# ── Auth ───────────────────────────────────────────────────────────────────────

def test_list_jobs_public():
    """GET /jobs/ requires no auth — public read endpoint."""
    c = Client(HTTP_HOST="demo.localhost")
    res = c.get("/api/evidence/jobs/")
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_create_job_requires_auth():
    """POST /jobs/ without key returns 401."""
    c = Client(HTTP_HOST="demo.localhost")
    res = _post_json(c, "/api/evidence/jobs/", {"n_samples": 1})
    assert res.status_code == 401


def test_get_job_public(job):
    """GET /jobs/{id}/ requires no auth."""
    with schema_context("demo"):
        c = Client(HTTP_HOST="demo.localhost")
        res = c.get(f"/api/evidence/jobs/{job.id}/")
        assert res.status_code == 200
        assert res.json()["id"] == job.id


# ── Jobs ───────────────────────────────────────────────────────────────────────

def test_create_job(api_key):
    with schema_context("demo"):
        c = _client(api_key)
        res = _post_json(c, "/api/evidence/jobs/", {"n_samples": 1})
        assert res.status_code == 200
        data = res.json()
        assert "id" in data
        assert data["status"] == "PENDING"
        assert data["n_samples"] == 1


def test_get_job(job, api_key):
    with schema_context("demo"):
        c = _client(api_key)
        res = c.get(f"/api/evidence/jobs/{job.id}/")
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == job.id
        assert data["status"] == "PENDING"
        assert "paper_count" in data
        assert "claim_count" in data
        assert "answer_count" in data


def test_get_job_404(api_key):
    with schema_context("demo"):
        c = _client(api_key)
        res = c.get("/api/evidence/jobs/999999/")
        assert res.status_code == 404


# ── Papers ─────────────────────────────────────────────────────────────────────

def test_list_papers_empty(job, api_key):
    with schema_context("demo"):
        c = _client(api_key)
        res = c.get(f"/api/evidence/jobs/{job.id}/papers/")
        assert res.status_code == 200
        assert res.json() == []


def test_list_papers_with_data(job, paper_a, paper_b, api_key):
    with schema_context("demo"):
        c = _client(api_key)
        res = c.get(f"/api/evidence/jobs/{job.id}/papers/")
        assert res.status_code == 200
        papers = res.json()
        assert len(papers) == 2
        titles = [p["title"] for p in papers]
        assert "Paper A" in titles
        assert "Paper B" in titles


# ── Claims ─────────────────────────────────────────────────────────────────────

def test_list_claims_empty(job, api_key):
    with schema_context("demo"):
        c = _client(api_key)
        res = c.get(f"/api/evidence/jobs/{job.id}/claims/")
        assert res.status_code == 200
        assert res.json() == []


def test_list_claims_with_data(job, claim_a, claim_b, api_key):
    with schema_context("demo"):
        c = _client(api_key)
        res = c.get(f"/api/evidence/jobs/{job.id}/claims/")
        assert res.status_code == 200
        claims = res.json()
        assert len(claims) == 2
        texts = [cl["text"] for cl in claims]
        assert "Drug X reduces tumor size by 40%." in texts


# ── Answers ────────────────────────────────────────────────────────────────────

def test_list_answers_empty(job, api_key):
    with schema_context("demo"):
        c = _client(api_key)
        res = c.get(f"/api/evidence/jobs/{job.id}/answers/")
        assert res.status_code == 200
        assert res.json() == []


def test_report_answer_counts(job, api_key):
    with schema_context("demo"):
        c = _client(api_key)
        res = c.get(f"/api/evidence/jobs/{job.id}/report/")
        assert res.status_code == 200
        data = res.json()
        assert "yes_count" in data
        assert "no_count" in data
        assert "maybe_count" in data


# ── Dispatch ───────────────────────────────────────────────────────────────────

def test_dispatch_job(job, api_key):
    with schema_context("demo"):
        c = _client(api_key)
        with patch("apps.evidence.tasks.dispatch.dispatch_analysis_job.delay"):
            res = _post_json(c, f"/api/evidence/jobs/{job.id}/dispatch/", {})
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "dispatched"


def test_dispatch_already_running_job(job, api_key):
    with schema_context("demo"):
        from apps.evidence.models import AnalysisJob
        job.status = AnalysisJob.Status.RUNNING
        job.save()
        c = _client(api_key)
        res = _post_json(c, f"/api/evidence/jobs/{job.id}/dispatch/", {})
        assert res.status_code == 400


# ── Report ─────────────────────────────────────────────────────────────────────

def test_get_report(job, api_key):
    with schema_context("demo"):
        c = _client(api_key)
        res = c.get(f"/api/evidence/jobs/{job.id}/report/")
        assert res.status_code == 200
        data = res.json()
        assert data["job_id"] == job.id
        assert "total_claims" in data
        assert "total_answers" in data
        assert "yes_count" in data
        assert "no_count" in data
        assert "maybe_count" in data
