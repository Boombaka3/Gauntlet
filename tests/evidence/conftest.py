# tests/evidence/conftest.py
import secrets

import pytest
from django_tenants.utils import schema_context


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        with schema_context("public"):
            from apps.core.models import Domain, Tenant
            tenant, _ = Tenant.objects.get_or_create(
                schema_name="demo",
                defaults={"name": "Test Org"},
            )
            Domain.objects.get_or_create(
                domain="demo.localhost",
                defaults={"tenant": tenant, "is_primary": True},
            )


@pytest.fixture
def job(db):
    with schema_context("demo"):
        from apps.evidence.models import AnalysisJob
        j = AnalysisJob.objects.create(n_samples=1)
        yield j


@pytest.fixture
def paper_a(job):
    with schema_context("demo"):
        from apps.evidence.models import Paper
        p = Paper.objects.create(job=job, title="Paper A", s3_key="test/paper_a.pdf")
        yield p


@pytest.fixture
def paper_b(job):
    with schema_context("demo"):
        from apps.evidence.models import Paper
        p = Paper.objects.create(job=job, title="Paper B", s3_key="test/paper_b.pdf")
        yield p


@pytest.fixture
def claim_a(paper_a):
    with schema_context("demo"):
        from apps.evidence.models import Claim
        c = Claim.objects.create(
            paper=paper_a,
            text="Drug X reduces tumor size by 40%.",
            claim_type="causal",
            source_sentence="Drug X reduces tumor size by 40% in mouse models.",
        )
        yield c


@pytest.fixture
def claim_b(paper_b):
    with schema_context("demo"):
        from apps.evidence.models import Claim
        c = Claim.objects.create(
            paper=paper_b,
            text="Drug X shows no significant effect on tumor size.",
            claim_type="factual",
            source_sentence="Drug X shows no significant effect in clinical trials.",
        )
        yield c


@pytest.fixture
def api_key(db):
    with schema_context("public"):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        user, _ = User.objects.get_or_create(
            username="testuser",
            defaults={"email": "test@evidence.local", "is_active": True},
        )
        if not user.api_key:
            user.api_key = secrets.token_urlsafe(32)
            user.save()
        return user.api_key
