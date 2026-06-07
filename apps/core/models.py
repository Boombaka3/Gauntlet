# llm_eval_harness/apps/core/models.py
from django.db import models
from django_tenants.models import DomainMixin, TenantMixin


class Tenant(TenantMixin):
    """
    One row per customer/team. django-tenants creates a dedicated PostgreSQL
    schema named after schema_name for each tenant's data isolation.
    """
    auto_create_schema = True

    name = models.CharField(max_length=255, blank=True)

    class Meta:
        app_label = "core"


class Domain(DomainMixin):
    """
    Maps hostnames to tenants. A single tenant may have multiple domains.
    The public schema is served under the domain marked is_primary=True
    with tenant pointing to the shared Tenant row.
    """

    class Meta:
        app_label = "core"
