from __future__ import annotations

try:
    from celery.result import AsyncResult
except Exception:  # pragma: no cover - optional dependency in lightweight dev envs
    AsyncResult = None

from fastapi import APIRouter, Depends

from backend.celery_app import celery_app
from backend.security import require_current_user
try:
    from backend.tasks.scrape_tasks import get_local_task_state
except Exception:
    def get_local_task_state(task_id: str):
        return None


api_router = APIRouter(prefix="/api/tasks", tags=["Tasks"], dependencies=[Depends(require_current_user)])
router = api_router


def _normalize_status(state: str) -> str:
    state = (state or "").upper()
    if state == "SUCCESS":
        return "completed"
    if state in {"FAILURE", "REVOKED"}:
        return "failed"
    if state in {"STARTED", "RETRY", "PROGRESS"}:
        return "running"
    return "pending"


@api_router.get("/{task_id}/status")
def task_status(task_id: str):
    local = get_local_task_state(task_id)
    if local:
        return local

    async_result = None
    if AsyncResult is not None:
        try:
            async_result = AsyncResult(task_id, app=celery_app)
        except Exception:
            async_result = None
    if async_result is None:
        return {"task_id": task_id, "status": "pending", "result": None, "error": None, "task_name": None}

    normalized_status = _normalize_status(async_result.state)
    result_payload = None
    error_payload = None

    if normalized_status == "completed":
        result_payload = async_result.result
    elif normalized_status == "failed":
        error_payload = str(async_result.result or async_result.traceback or "Task failed")
    elif async_result.info not in (None, ""):
        result_payload = async_result.info

    return {
        "task_id": task_id,
        "status": normalized_status,
        "result": result_payload,
        "error": error_payload,
        "task_name": getattr(async_result, "name", None),
    }
