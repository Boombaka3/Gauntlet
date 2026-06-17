# apps/evidence/tasks/dispatch.py
import logging
import os

from celery import chord, group, shared_task
from django.utils import timezone
from django_tenants.utils import schema_context

logger = logging.getLogger(__name__)

_SCHEMA = os.getenv("GAUNTLET_TENANT_SCHEMA", "demo")


@shared_task(bind=True, max_retries=0)
def dispatch_analysis_job(self, job_id: int):
    try:
        with schema_context(_SCHEMA):
            from apps.evidence.models import AnalysisJob
            from apps.evidence.tasks.extract_claims import extract_claims
            from apps.evidence.tasks.answer_questions import answer_paper_questions

            job = AnalysisJob.objects.get(id=job_id)
            job.status = AnalysisJob.Status.RUNNING
            job.started_at = timezone.now()
            job.save(update_fields=["status", "started_at"])

            paper_ids = list(job.papers.values_list("id", flat=True))

            if not paper_ids:
                logger.error("Job %s: no papers uploaded", job_id)
                job.status = AnalysisJob.Status.FAILED
                job.finished_at = timezone.now()
                job.save(update_fields=["status", "finished_at"])
                return

            extraction_group = group(
                extract_claims.si(pid) for pid in paper_ids
            )

            answer_group = group(
                answer_paper_questions.si(pid, job.n_samples)
                for pid in paper_ids
            )

            pipeline = chord(extraction_group)(
                chord(answer_group)(
                    _mark_done.si(job_id)
                )
            )

            logger.info(
                "Job %s: dispatched pipeline for %d papers", job_id, len(paper_ids)
            )

    except Exception as e:
        logger.error(
            "dispatch_analysis_job failed for job %s: %s", job_id, e, exc_info=True
        )
        try:
            with schema_context(_SCHEMA):
                from apps.evidence.models import AnalysisJob as AJ
                AJ.objects.filter(id=job_id).update(
                    status=AJ.Status.FAILED,
                    finished_at=timezone.now(),
                )
        except Exception as inner:
            logger.error("Could not mark job %s FAILED: %s", job_id, inner)


@shared_task(bind=True, max_retries=0)
def _mark_done(self, job_id: int):
    try:
        with schema_context(_SCHEMA):
            from apps.evidence.models import AnalysisJob
            job = AnalysisJob.objects.get(id=job_id)
            job.status = AnalysisJob.Status.DONE
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "finished_at"])
            logger.info("Job %s: DONE", job_id)
    except Exception as e:
        logger.error("_mark_done failed for job %s: %s", job_id, e)
