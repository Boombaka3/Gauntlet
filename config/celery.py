# llm_eval_harness/config/celery.py
import os

import django
from celery import Celery
from django.conf import settings

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Guard: config/__init__.py causes this module to be imported by Django's own
# startup (when it loads ROOT_URLCONF), at which point django.setup() has
# already been called.  The try/except prevents the RuntimeError from
# "populate() has already been called."
try:
    django.setup()
except RuntimeError:
    pass

app = Celery("evidence_trace")
app.config_from_object("django.conf:settings", namespace="CELERY")
# force=True: import task modules immediately so @shared_task decorators fire
# now rather than waiting for the worker's deferred finalize() signal.
app.autodiscover_tasks(["apps.evidence"], force=True)
