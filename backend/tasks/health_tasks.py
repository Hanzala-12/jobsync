from __future__ import annotations

try:
    from celery import shared_task
except Exception:  # pragma: no cover - optional dependency in lightweight dev envs
    def shared_task(name=None, bind=False):
        def _decorator(func):
            return func

        return _decorator

from backend.monitoring import record_celery_task


@shared_task(name="backend.tasks.health_task")
def health_task(payload: str = "ok") -> dict:
    result = {"ok": True, "payload": payload}
    record_celery_task("backend.tasks.health_task", "completed")
    return result


@shared_task(name="backend.tasks.add")
def add(x: int, y: int) -> int:
    result = int(x) + int(y)
    record_celery_task("backend.tasks.add", "completed")
    return result
