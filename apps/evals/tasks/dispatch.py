# llm_eval_harness/apps/evals/tasks/dispatch.py
import logging

from celery import chord, group, shared_task
from django.utils import timezone
from django_tenants.utils import schema_context

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="evals.dispatch_eval_run")
def dispatch_eval_run(self, eval_run_id: int, schema_name: str) -> None:
    """
    Fan-out task: creates ModelRuns and fires a Celery chord that runs all
    model calls in parallel, then triggers score_all_results when they finish.
    """
    from apps.evals.models import EvalRun, ModelRun
    from apps.evals.tasks.run_model import run_model
    from apps.evals.tasks.score import score_all_results

    try:
        with schema_context(schema_name):
            eval_run = EvalRun.objects.select_related("suite").get(id=eval_run_id)
            eval_run.status = EvalRun.Status.DISPATCHED
            eval_run.started_at = timezone.now()
            eval_run.save(update_fields=["status", "started_at"])

            cases = list(eval_run.suite.cases.all())
            model_ids: list[str] = eval_run.model_ids

            if not cases or not model_ids:
                logger.warning(
                    "EvalRun %s has no cases or models; marking DONE immediately", eval_run_id
                )
                eval_run.status = EvalRun.Status.DONE
                eval_run.finished_at = timezone.now()
                eval_run.save(update_fields=["status", "finished_at"])
                return

            model_runs = []
            for case in cases:
                for model_id in model_ids:
                    mr = ModelRun.objects.create(
                        eval_run=eval_run,
                        prompt_case=case,
                        model_id=model_id,
                        status=ModelRun.Status.PENDING,
                    )
                    model_runs.append(mr)

            logger.info(
                "EvalRun %s: dispatching %d ModelRuns", eval_run_id, len(model_runs)
            )

            task_group = group(
                run_model.si(mr.id, schema_name) for mr in model_runs
            )
            callback = score_all_results.si(eval_run_id, schema_name)
            chord(task_group)(callback)

            eval_run.status = EvalRun.Status.RUNNING
            eval_run.save(update_fields=["status"])

    except Exception as exc:
        logger.error(
            "dispatch_eval_run failed for EvalRun %s: %s", eval_run_id, exc, exc_info=True
        )
        try:
            with schema_context(schema_name):
                from apps.evals.models import EvalRun as ER
                ER.objects.filter(id=eval_run_id).update(
                    status=ER.Status.FAILED,
                    finished_at=timezone.now(),
                )
        except Exception as inner:
            logger.error("Could not mark EvalRun %s FAILED: %s", eval_run_id, inner)
