# C:\LLM Eval Harness\llm_eval_harness\tests\conftest.py
import pytest
from django_tenants.utils import schema_context

DEMO_SCHEMA = "demo"


@pytest.fixture(scope="session")
def django_db_setup(django_db_setup, django_db_blocker):
    """
    Extends pytest-django's default DB setup to ensure the demo tenant row and
    schema exist before any test runs.  The parameter 'django_db_setup' resolves
    to the plugin-provided fixture (not this one), so there is no circular ref.
    """
    with django_db_blocker.unblock():
        with schema_context("public"):
            from apps.core.models import Domain, Tenant

            tenant, _ = Tenant.objects.get_or_create(
                schema_name=DEMO_SCHEMA,
                defaults={"name": "Demo Tenant"},
            )
            Domain.objects.get_or_create(
                domain="demo.localhost",
                tenant=tenant,
                defaults={"is_primary": True},
            )


@pytest.fixture
def tenant_schema(db):
    """
    Activate the demo tenant schema for the duration of a single test.
    All ORM queries inside the test will target the 'demo' PostgreSQL schema.
    """
    with schema_context(DEMO_SCHEMA):
        yield DEMO_SCHEMA


@pytest.fixture
def client(tenant_schema):
    """
    Django test client pre-configured with the Host header that the
    TenantMainMiddleware uses to resolve the demo tenant.
    """
    from django.test import Client

    return Client(HTTP_HOST="demo.localhost")
