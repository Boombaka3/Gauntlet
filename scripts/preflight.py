# llm_eval_harness/scripts/preflight.py
"""
Run before server start to verify all external dependencies are reachable.
Exits with code 1 on first failure so Docker health checks and orchestrators
can detect a broken environment before traffic reaches the app.
"""
import os
import sys

# Ensure project root is on the path when run as a standalone script.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from dotenv import load_dotenv

load_dotenv()

import django

django.setup()

import logging

import boto3
import redis
from botocore.exceptions import BotoCoreError, ClientError
from django.conf import settings
from django.db import connection
from django.db.utils import OperationalError

logger = logging.getLogger(__name__)


def check_database() -> None:
    try:
        connection.ensure_connection()
        logger.info("[preflight] Database OK")
    except OperationalError as exc:
        logger.error("[preflight] Database FAILED: %s", exc)
        sys.exit(1)


def check_redis() -> None:
    try:
        client = redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=5)
        client.ping()
        logger.info("[preflight] Redis OK")
    except Exception as exc:
        logger.error("[preflight] Redis FAILED: %s", exc)
        sys.exit(1)


def check_minio() -> None:
    try:
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        existing = [b["Name"] for b in s3.list_buckets().get("Buckets", [])]
        if bucket not in existing:
            s3.create_bucket(Bucket=bucket)
            logger.info("[preflight] MinIO bucket '%s' created", bucket)
        else:
            logger.info("[preflight] MinIO bucket '%s' exists OK", bucket)
    except (BotoCoreError, ClientError) as exc:
        logger.error("[preflight] MinIO FAILED: %s", exc)
        sys.exit(1)
    except Exception as exc:
        logger.error("[preflight] MinIO FAILED (unexpected): %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    check_database()
    check_redis()
    check_minio()
    logger.info("[preflight] All checks passed.")
