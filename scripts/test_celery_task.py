"""Smoke test for the Celery worker.

Usage: python scripts/test_celery_task.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.celery_app import celery_app, configure_celery


def main() -> int:
    configure_celery()
    use_embedded_worker = os.getenv("CELERY_EMBEDDED_WORKER", "false").strip().lower() in {"1", "true", "yes", "on"}

    if use_embedded_worker:
        from celery.contrib.testing.worker import start_worker

        with start_worker(celery_app, perform_ping_check=False, pool="solo"):
            result = celery_app.send_task("backend.tasks.health_task", args=["celery-ok"])
            payload = result.get(timeout=30)
    else:
        result = celery_app.send_task("backend.tasks.health_task", args=["celery-ok"])
        payload = result.get(timeout=30)
    if not isinstance(payload, dict) or not payload.get("ok") or payload.get("payload") != "celery-ok":
        raise RuntimeError(f"Unexpected Celery payload: {payload!r}")

    print({"task_id": result.id, "status": result.status, "payload": payload})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
