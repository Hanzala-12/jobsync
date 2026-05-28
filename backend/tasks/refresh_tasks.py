from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    from celery import shared_task
except Exception:  # pragma: no cover - optional dependency in lightweight dev envs
    def shared_task(name=None, bind=False):
        def _decorator(func):
            return func

        return _decorator

from backend.celery_app import celery_enabled
from backend.monitoring import record_celery_task
from backend.tasks.state import new_task_id, record_task_state
def run_refresh_verified_data_job(limit=None, country=None, priority_limit=100, priority_age_days=30):
    # University module removed — refresh job disabled.
    return {"message": "university module removed; refresh disabled", "items_processed": 0}


_logger = logging.getLogger(__name__)
_TASK_NAME = "backend.tasks.refresh_tasks.refresh_verified_data"


def _run_refresh(limit: Optional[int], country: Optional[str], priority_limit: int, priority_age_days: int) -> Dict[str, Any]:
    return run_refresh_verified_data_job(
        limit=limit,
        country=country,
        priority_limit=priority_limit,
        priority_age_days=priority_age_days,
    )


@shared_task(name=_TASK_NAME, bind=True)
def refresh_verified_data_task(
    self,
    limit: Optional[int] = None,
    country: Optional[str] = None,
    priority_limit: int = 100,
    priority_age_days: int = 30,
) -> Dict[str, Any]:
    try:
        result = _run_refresh(limit, country, priority_limit, priority_age_days)
        record_celery_task(_TASK_NAME, "completed")
        return result
    except Exception:
        record_celery_task(_TASK_NAME, "failed")
        raise


def dispatch_refresh_verified_data(
    limit: Optional[int] = None,
    country: Optional[str] = None,
    priority_limit: int = 100,
    priority_age_days: int = 30,
) -> Dict[str, Any]:
    task_id = new_task_id()
    payload = {
        "limit": limit,
        "country": country,
        "priority_limit": priority_limit,
        "priority_age_days": priority_age_days,
    }
    record_task_state(task_id, "pending", task_name=_TASK_NAME, result=payload)

    if celery_enabled():
        try:
            async_result = refresh_verified_data_task.apply_async(kwargs=payload, task_id=task_id)
            return {"task_id": async_result.id, "status": "pending", "mode": "celery"}
        except Exception as exc:
            _logger.warning("Celery enqueue failed for refresh job; running locally instead: %s", exc)

    try:
        record_task_state(task_id, "running", task_name=_TASK_NAME, result=payload)
        result = _run_refresh(limit, country, priority_limit, priority_age_days)
        record_task_state(task_id, "completed", task_name=_TASK_NAME, result=result)
        record_celery_task(_TASK_NAME, "completed")
        return {"task_id": task_id, "status": "completed", "mode": "sync", "result": result}
    except Exception as exc:
        record_task_state(task_id, "failed", task_name=_TASK_NAME, error=str(exc))
        record_celery_task(_TASK_NAME, "failed")
        raise
