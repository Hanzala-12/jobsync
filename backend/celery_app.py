from __future__ import annotations

import logging
import os
from typing import Optional

try:
    from celery import Celery
    _HAS_CELERY = True
except Exception:  # pragma: no cover - Celery optional in lightweight dev envs
    Celery = None
    _HAS_CELERY = False
from fastapi import FastAPI


_logger = logging.getLogger(__name__)

ENABLE_CELERY = os.getenv("ENABLE_CELERY", "false").strip().lower() in {"1", "true", "yes", "on"}
CELERY_BROKER_URL = (os.getenv("CELERY_BROKER_URL") or "redis://localhost:6379/0").strip()
CELERY_RESULT_BACKEND = (os.getenv("CELERY_RESULT_BACKEND") or CELERY_BROKER_URL).strip()
CELERY_QUEUE_NAME = (os.getenv("CELERY_QUEUE_NAME") or "jobsync").strip() or "jobsync"

if _HAS_CELERY and Celery is not None:
    celery_app = Celery("jobsync")
    celery_app.conf.update(
        broker_url=CELERY_BROKER_URL,
        result_backend=CELERY_RESULT_BACKEND,
        task_default_queue=CELERY_QUEUE_NAME,
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_track_started=True,
        broker_connection_retry_on_startup=True,
        worker_prefetch_multiplier=int(os.getenv("CELERY_WORKER_PREFETCH_MULTIPLIER", "1")),
        result_expires=int(os.getenv("CELERY_RESULT_EXPIRES_SECONDS", "86400")),
    )
else:
    class _DummyCelery:
        def __init__(self, *args, **kwargs):
            self.conf = {}

        def conf_update(self, *args, **kwargs):
            self.conf.update(kwargs)

        def conf(self):
            return self.conf

        def autodiscover_tasks(self, *args, **kwargs):
            return None

    celery_app = _DummyCelery()


def configure_celery(fastapi_app: Optional[FastAPI] = None) -> Celery:
    if fastapi_app is not None:
        celery_app.conf.update(
            fastapi_app_name=fastapi_app.title,
            fastapi_app_version=fastapi_app.version,
            fastapi_app_description=fastapi_app.description,
        )

    if _HAS_CELERY and hasattr(celery_app, "autodiscover_tasks"):
        try:
            celery_app.autodiscover_tasks(["backend"], related_name="tasks")
        except Exception:
            pass
    return celery_app


def celery_enabled() -> bool:
    return ENABLE_CELERY and _HAS_CELERY
