# apps/evidence/tasks/build_graph.py
import logging
import os
from itertools import combinations

from celery import shared_task
from django.utils import timezone
from django_tenants.utils import schema_context

logger = logging.getLogger(__name__)

_SCHEMA = os.getenv("GAUNTLET_TENANT_SCHEMA", "demo")


@shared_task(bind=True, max_retries=0)
def build_conflict_graph(self, job_id: int):
    try:
        with schema_context(_SCHEMA):
            from apps.evidence.models import AnalysisJob, Claim, ConflictPair, RewardScore
            from apps.evidence.scoring.reward_voting import compute_reward

            job = AnalysisJob.objects.get(id=job_id)
            job.status = AnalysisJob.Status.RUNNING
            job.save(update_fields=["status"])

            paper_ids = list(job.papers.values_list("id", flat=True))
            if len(paper_ids) < 2:
                logger.warning("Job %s: need at least 2 papers, got %d", job_id, len(paper_ids))
                job.status = AnalysisJob.Status.FAILED
                job.finished_at = timezone.now()
                job.save(update_fields=["status", "finished_at"])
                return

            all_claims = {
                pid: list(Claim.objects.filter(paper_id=pid).select_related("paper"))
                for pid in paper_ids
            }

            pairs_created = 0
            for pid_a, pid_b in combinations(paper_ids, 2):
                claims_a = all_claims.get(pid_a, [])
                claims_b = all_claims.get(pid_b, [])
                for ca in claims_a:
                    for cb in claims_b:
                        try:
                            conflict_pair, reward = compute_reward(
                                ca, cb, n_samples=job.n_samples
                            )
                            conflict_pair.save()
                            reward.conflict_pair = conflict_pair
                            reward.save()
                            pairs_created += 1
                        except Exception as e:
                            logger.error(
                                "Conflict pair failed (%s, %s): %s", ca.id, cb.id, e
                            )

            logger.info("Job %s: created %d conflict pairs", job_id, pairs_created)
            job.status = AnalysisJob.Status.DONE
            job.finished_at = timezone.now()
            job.save(update_fields=["status", "finished_at"])

    except Exception as e:
        logger.error("build_conflict_graph failed for job %s: %s", job_id, e, exc_info=True)
        try:
            with schema_context(_SCHEMA):
                from apps.evidence.models import AnalysisJob as AJ
                AJ.objects.filter(id=job_id).update(
                    status=AJ.Status.FAILED,
                    finished_at=timezone.now(),
                )
        except Exception as inner:
            logger.error("Could not mark job %s FAILED: %s", job_id, inner)
