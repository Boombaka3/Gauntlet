# apps/evidence/tasks/extract_claims.py
import json
import logging
import os
from pathlib import Path

import anthropic
import boto3
from celery import shared_task
from django.conf import settings
from django_tenants.utils import schema_context

logger = logging.getLogger(__name__)

EXTRACTOR_PROMPT = (Path(__file__).parent.parent / "prompts" / "claim_extractor.txt").read_text()
_SCHEMA = os.getenv("GAUNTLET_TENANT_SCHEMA", "demo")


@shared_task(bind=True, max_retries=0)
def extract_claims(self, paper_id: int):
    try:
        with schema_context(_SCHEMA):
            from apps.evidence.models import Claim, Paper
            from apps.evidence.utils.pdf_parser import extract_sections, get_main_sections

            paper = Paper.objects.get(id=paper_id)

            s3 = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )
            obj = s3.get_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=paper.s3_key)
            pdf_bytes = obj["Body"].read()

            all_sections = extract_sections(pdf_bytes)
            sections = get_main_sections(all_sections)
            paper.parsed_sections = sections
            paper.save(update_fields=["parsed_sections"])

            client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
            claims_created = 0

            for section_name, section_text in sections.items():
                if not section_text.strip():
                    continue
                prompt = EXTRACTOR_PROMPT.replace("{section_text}", section_text[:3000])
                try:
                    response = client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=1024,
                        messages=[{"role": "user", "content": prompt}],
                    )
                    raw = response.content[0].text.strip()
                    data = json.loads(raw)
                    for c in data.get("claims", []):
                        if not isinstance(c, dict) or not c.get("text"):
                            continue
                        Claim.objects.create(
                            paper=paper,
                            text=str(c.get("text", ""))[:2000],
                            claim_type=str(c.get("type", "factual"))[:20],
                            entities=c.get("entities") if isinstance(c.get("entities"), list) else [],
                            section=str(c.get("section", section_name))[:100],
                            source_sentence=str(c.get("source_sentence", ""))[:500],
                            confidence=float(c["confidence"]) if c.get("confidence") is not None else None,
                        )
                        claims_created += 1
                except Exception as e:
                    logger.error("Claim extraction failed for section %s: %s", section_name, e)

            logger.info("Paper %s: extracted %d claims", paper_id, claims_created)

    except Exception as e:
        logger.error("extract_claims failed for paper %s: %s", paper_id, e, exc_info=True)
