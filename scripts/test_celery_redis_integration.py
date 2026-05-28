from __future__ import annotations

import argparse
import os
import sys
import time

import redis

from backend.celery_app import CELERY_BROKER_URL, CELERY_RESULT_BACKEND, celery_app


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a production-like Celery + Redis integration smoke test")
    parser.add_argument("--timeout", type=int, default=30, help="Seconds to wait for the task result")
    parser.add_argument("--broker-url", default=os.getenv("CELERY_BROKER_URL", CELERY_BROKER_URL), help="Celery broker URL")
    parser.add_argument("--result-backend", default=os.getenv("CELERY_RESULT_BACKEND", CELERY_RESULT_BACKEND), help="Celery result backend URL")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()

    redis_client = redis.from_url(args.broker_url)
    redis_client.ping()

    celery_app.conf.broker_url = args.broker_url
    celery_app.conf.result_backend = args.result_backend

    task = celery_app.send_task("backend.tasks.add", args=[4, 5])
    started = time.time()
    result = task.get(timeout=args.timeout)
    elapsed = round(time.time() - started, 2)

    if int(result) != 9:
        raise AssertionError(f"Unexpected task result: {result!r}")

    print({"task_id": task.id, "status": "SUCCESS", "payload": result, "elapsed_seconds": elapsed})
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"Celery Redis integration test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)