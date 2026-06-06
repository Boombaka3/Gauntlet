# llm_eval_harness/apps/evals/tasks/score.py
import json
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django_tenants.utils import schema_context

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="evals.score_all_results")
def score_all_results(self, eval_run_id: int, schema_name: str) -> None:
    """
    Chord callback — fires after all run_model tasks complete.
    Scores every DONE ModelRun and writes one ScoreResult per run via bulk_create.
    Assembles a JSON report and uploads it to S3, then marks EvalRun DONE.
    """
    from apps.evals.models import EvalRun, ModelRun, ScoreResult

    try:
        with schema_context(schema_name):
            eval_run = EvalRun.objects.select_related("suite").get(id=eval_run_id)

            done_runs = list(
                ModelRun.objects
                .filter(eval_run=eval_run, status=ModelRun.Status.DONE)
                .select_related("prompt_case", "prompt_case__suite", "eval_run")
            )

            logger.info(
                "score_all_results: EvalRun %s — %d DONE ModelRuns to score",
                eval_run_id,
                len(done_runs),
            )

            score_mode = eval_run.score_mode
            baseline_run_id = eval_run.baseline_run_id
            score_results: list[ScoreResult] = []

            for model_run in done_runs:
                try:
                    result = _score_one(model_run, score_mode, baseline_run_id)
                    score_results.append(result)
                except Exception as exc:
                    logger.error(
                        "Scoring failed for ModelRun %s: %s", model_run.id, exc, exc_info=True
                    )

            ScoreResult.objects.bulk_create(score_results, ignore_conflicts=True)

            scored = [r for r in score_results if r.overall is not None]
            overall_avg = (
                sum(r.overall for r in scored) / len(scored)
                if scored
                else None
            )

            report = {
                "run_id": eval_run_id,
                "suite_id": eval_run.suite_id,
                "score_mode": score_mode,
                "overall_avg": round(overall_avg, 4),
                "results": [
                    {
                        "model_run_id": r.model_run_id,
                        "model_id": r.model_run.model_id,
                        "overall": r.overall,
                        "passed": r.passed,
                        "regression_delta": r.regression_delta,
                        "scores": r.scores,
                    }
                    for r in score_results
                ],
            }

            s3_key = _upload_report(schema_name, eval_run_id, report)

            eval_run.result_s3_key = s3_key
            eval_run.status = EvalRun.Status.DONE
            eval_run.finished_at = timezone.now()
            eval_run.save(update_fields=["status", "finished_at", "result_s3_key"])

            logger.info(
                "EvalRun %s DONE — %d scored, overall_avg=%.3f",
                eval_run_id,
                len(score_results),
                overall_avg,
            )

    except Exception as exc:
        logger.error(
            "score_all_results failed for EvalRun %s: %s", eval_run_id, exc, exc_info=True
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


def _score_one(model_run, score_mode: str, baseline_run_id: int | None):
    from apps.evals.models import EvalRun
    from apps.evals.scoring.exact_match import score_exact_match
    from apps.evals.scoring.llm_judge import score_llm_judge
    from apps.evals.scoring.regression import score_regression
    from apps.evals.scoring.rubric import score_rubric

    if score_mode == EvalRun.ScoreMode.EXACT_MATCH:
        return score_exact_match(model_run)

    if score_mode == EvalRun.ScoreMode.RUBRIC:
        rubric = model_run.prompt_case.suite.rubric
        return score_rubric(model_run, rubric)

    if score_mode == EvalRun.ScoreMode.LLM_JUDGE:
        return score_llm_judge(model_run)

    if score_mode == EvalRun.ScoreMode.REGRESSION:
        if baseline_run_id is None:
            raise ValueError(f"EvalRun has score_mode=regression but no baseline_run_id")
        return score_regression(model_run, baseline_run_id)

    raise ValueError(f"Unknown score_mode: {score_mode}")


def _upload_report(schema_name: str, eval_run_id: int, report: dict) -> str | None:
    key = f"evals/{schema_name}/{eval_run_id}/report.json"
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        s3.put_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=key,
            Body=json.dumps(report, default=str).encode("utf-8"),
            ContentType="application/json",
        )
        return key
    except (BotoCoreError, ClientError) as exc:
        logger.error("S3 report upload failed for key %s: %s", key, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected S3 error uploading report %s: %s", key, exc)
        return None
