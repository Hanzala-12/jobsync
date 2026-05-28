from __future__ import annotations

import os
from typing import Optional

try:
    from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest
except Exception:  # pragma: no cover - optional dependency in lightweight test envs
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"

    class _NoOpMetric:
        def labels(self, *args, **kwargs):
            return self

        def inc(self, *args, **kwargs):
            return None

        def observe(self, *args, **kwargs):
            return None

    def generate_latest():  # type: ignore[no-redef]
        return b""

    def Counter(*args, **kwargs):  # type: ignore[no-redef]
        return _NoOpMetric()

    def Histogram(*args, **kwargs):  # type: ignore[no-redef]
        return _NoOpMetric()


ENABLE_METRICS = os.getenv("ENABLE_METRICS", "false").strip().lower() in {"1", "true", "yes", "on"}

http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests processed by the API",
    ["method", "endpoint", "status"],
)

scrape_jobs_total = Counter(
    "scrape_jobs_total",
    "Total program scrape jobs by final status",
    ["status"],
)

scrape_duration_seconds = Histogram(
    "scrape_duration_seconds",
    "Duration of program scraping jobs in seconds",
)

celery_tasks_total = Counter(
    "celery_tasks_total",
    "Total Celery tasks by task name and final status",
    ["task_name", "status"],
)


def record_http_request(method: str, endpoint: str, status: int) -> None:
    if not ENABLE_METRICS:
        return
    http_requests_total.labels(method=method.upper(), endpoint=endpoint or "unknown", status=str(status)).inc()


def record_scrape_job(status: str, duration_seconds: Optional[float] = None) -> None:
    if not ENABLE_METRICS:
        return
    scrape_jobs_total.labels(status=(status or "unknown").lower()).inc()
    if duration_seconds is not None and duration_seconds >= 0:
        scrape_duration_seconds.observe(duration_seconds)


def record_celery_task(task_name: str, status: str) -> None:
    if not ENABLE_METRICS:
        return
    celery_tasks_total.labels(task_name=task_name or "unknown", status=(status or "unknown").lower()).inc()


def metrics_payload() -> tuple[str, str]:
    return generate_latest().decode("utf-8"), CONTENT_TYPE_LATEST
