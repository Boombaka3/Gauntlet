# llm_eval_harness/scripts/seed.py
"""
Creates a demo tenant and a sample EvalSuite with two PromptCases.
Safe to run multiple times — skips creation if objects already exist.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from dotenv import load_dotenv

load_dotenv()

import django

django.setup()

import logging

from apps.core.models import Domain, Tenant

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def create_demo_tenant() -> Tenant:
    tenant, created = Tenant.objects.get_or_create(
        schema_name="demo",
        defaults={"name": "Demo Tenant"},
    )
    if created:
        Domain.objects.create(domain="demo.localhost", tenant=tenant, is_primary=True)
        logger.info("Created demo tenant (schema: demo)")
    else:
        logger.info("Demo tenant already exists")
    return tenant


def seed_eval_suite(tenant: Tenant) -> None:
    from django_tenants.utils import schema_context

    with schema_context(tenant.schema_name):
        from apps.evals.models import EvalSuite, PromptCase

        suite, created = EvalSuite.objects.get_or_create(
            name="Demo Suite",
            defaults={
                "version": 1,
                "description": "A sample evaluation suite for smoke-testing the harness.",
                "rubric": [
                    {"criterion": "Correctness", "weight": 0.5},
                    {"criterion": "Clarity", "weight": 0.3},
                    {"criterion": "Conciseness", "weight": 0.2},
                ],
            },
        )
        if created:
            logger.info("Created EvalSuite: %s", suite)
        else:
            logger.info("EvalSuite already exists: %s", suite)

        cases = [
            {
                "name": "Capital of France",
                "system_prompt": "You are a helpful geography assistant.",
                "user_prompt": "What is the capital of France?",
                "expected_output": "Paris",
                "tags": ["geography", "factual"],
            },
            {
                "name": "Python list comprehension",
                "system_prompt": "You are a Python tutor.",
                "user_prompt": "Write a list comprehension that squares numbers 1-10.",
                "expected_output": "[x**2 for x in range(1, 11)]",
                "tags": ["python", "code"],
            },
        ]
        for case_data in cases:
            obj, created = PromptCase.objects.get_or_create(
                suite=suite,
                name=case_data["name"],
                defaults={k: v for k, v in case_data.items() if k != "name"},
            )
            if created:
                logger.info("  Created PromptCase: %s", obj.name)
            else:
                logger.info("  PromptCase already exists: %s", obj.name)


if __name__ == "__main__":
    tenant = create_demo_tenant()
    seed_eval_suite(tenant)
    logger.info("Seed complete.")
