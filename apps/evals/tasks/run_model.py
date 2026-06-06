# llm_eval_harness/apps/evals/tasks/run_model.py
import json
import logging

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from celery import shared_task
from django.conf import settings
from django_tenants.utils import schema_context

logger = logging.getLogger(__name__)


@shared_task(bind=True, name="evals.run_model")
def run_model(self, model_run_id: int, schema_name: str) -> None:
    """
    Executes one (PromptCase × model_id) pair.
    Never raises — all outcomes are reflected in ModelRun.status.
    """
    from apps.evals.adapters.base import ModelAdapter
    from apps.evals.models import ModelRun

    try:
        with schema_context(schema_name):
            model_run = (
                ModelRun.objects
                .select_related("prompt_case", "eval_run")
                .get(id=model_run_id)
            )
            model_run.status = ModelRun.Status.RUNNING
            model_run.save(update_fields=["status"])

            adapter = ModelAdapter.from_model_id(model_run.model_id)
            result = adapter.complete(
                system_prompt=model_run.prompt_case.system_prompt,
                user_prompt=model_run.prompt_case.user_prompt,
            )

            model_run.raw_output = result.output or ""
            model_run.latency_ms = result.latency_ms
            model_run.token_count = result.token_count
            model_run.error_message = result.error

            if result.error:
                model_run.status = ModelRun.Status.FAILED
                logger.warning(
                    "ModelRun %s FAILED (model=%s): %s",
                    model_run_id,
                    model_run.model_id,
                    result.error,
                )
            else:
                s3_key = _upload_raw_output(
                    schema_name=schema_name,
                    eval_run_id=model_run.eval_run_id,
                    model_run_id=model_run_id,
                    content=result.output,
                )
                model_run.s3_key = s3_key
                model_run.status = ModelRun.Status.DONE
                logger.info(
                    "ModelRun %s DONE (model=%s, latency=%dms)",
                    model_run_id,
                    model_run.model_id,
                    result.latency_ms,
                )

            model_run.save(
                update_fields=[
                    "status",
                    "raw_output",
                    "latency_ms",
                    "token_count",
                    "error_message",
                    "s3_key",
                ]
            )

    except Exception as exc:
        logger.error(
            "run_model task failed for ModelRun %s: %s", model_run_id, exc, exc_info=True
        )
        try:
            with schema_context(schema_name):
                from apps.evals.models import ModelRun as MR
                MR.objects.filter(id=model_run_id).update(
                    status=MR.Status.FAILED,
                    error_message=str(exc)[:1000],
                )
        except Exception as inner:
            logger.error(
                "Could not mark ModelRun %s FAILED: %s", model_run_id, inner
            )


def _upload_raw_output(
    schema_name: str,
    eval_run_id: int,
    model_run_id: int,
    content: str,
) -> str | None:
    key = f"evals/{schema_name}/{eval_run_id}/{model_run_id}.txt"
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
            Body=content.encode("utf-8"),
            ContentType="text/plain",
        )
        return key
    except (BotoCoreError, ClientError) as exc:
        logger.error("S3 upload failed for key %s: %s", key, exc)
        return None
    except Exception as exc:
        logger.error("Unexpected S3 error for key %s: %s", key, exc)
        return None
