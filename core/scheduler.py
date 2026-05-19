from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Callable, Dict, Optional

from core.database import get_db
from core.deduplicator import daily_dedup_cleanup
from core.job_checker import check_oldest_jobs
from scrapers import (
    brightspyre_scraper,
    careers_page_scraper,
    indexed_jobs_scraper,
    linkedin_indexed_scraper,
    mustakbil_scraper,
    rozee_scraper,
)

logger = logging.getLogger(__name__)


@dataclass
class ScheduledTask:
    name: str
    frequency_hours: int
    runner: Callable
    notes: str = ""
    next_run_at: datetime = field(default_factory=datetime.now)
    last_run_at: Optional[datetime] = None
    last_result: Optional[dict] = None
    last_error: Optional[str] = None


def _with_db(callable_obj: Callable) -> dict:
    db = next(get_db())
    try:
        result = callable_obj(db)
        if isinstance(result, dict):
            return result
        return {"items": len(result) if result is not None else 0}
    finally:
        db.close()


SCHEDULED_TASKS: Dict[str, ScheduledTask] = {
    "rozee_scraper": ScheduledTask("rozee_scraper", 3, lambda db: rozee_scraper.run(db), "highest priority"),
    "mustakbil_scraper": ScheduledTask("mustakbil_scraper", 4, lambda db: mustakbil_scraper.run(db)),
    "linkedin_indexed": ScheduledTask("linkedin_indexed", 6, lambda db: linkedin_indexed_scraper.run(db)),
    "brightspyre_scraper": ScheduledTask("brightspyre_scraper", 6, lambda db: brightspyre_scraper.run(db)),
    "careers_page": ScheduledTask("careers_page", 8, lambda db: careers_page_scraper.run(db)),
    "indexed_jobs": ScheduledTask("indexed_jobs", 8, lambda db: indexed_jobs_scraper.run(db)),
    "job_checker": ScheduledTask("job_checker", 1, lambda db: check_oldest_jobs(db, limit=50), "checks 50 oldest jobs"),
    "dedup_cleanup": ScheduledTask("dedup_cleanup", 24, lambda db: daily_dedup_cleanup(db)),
}

_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()


def registered_tasks() -> list[dict]:
    return [
        {
            "name": task.name,
            "frequency_hours": task.frequency_hours,
            "notes": task.notes,
            "last_run_at": task.last_run_at.isoformat() if task.last_run_at else None,
            "next_run_at": task.next_run_at.isoformat(),
            "last_error": task.last_error,
        }
        for task in SCHEDULED_TASKS.values()
    ]


def run_task(name: str) -> dict:
    if name not in SCHEDULED_TASKS:
        raise KeyError(f"Unknown scheduled task: {name}")

    task = SCHEDULED_TASKS[name]
    try:
        result = _with_db(task.runner)
        task.last_result = result
        task.last_error = None
        task.last_run_at = datetime.now()
        task.next_run_at = task.last_run_at + timedelta(hours=task.frequency_hours)
        return result
    except Exception as exc:
        task.last_error = str(exc)
        logger.exception("Scheduled task failed: %s", name)
        return {"error": str(exc)}


def run_due_tasks_once() -> dict:
    now = datetime.now()
    results = {}
    for task in SCHEDULED_TASKS.values():
        if task.next_run_at <= now:
            results[task.name] = run_task(task.name)
    return results


def start_scheduler() -> None:
    """Start the lightweight in-process scheduler when explicitly enabled."""
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop_event.clear()

    def loop() -> None:
        while not _stop_event.is_set():
            run_due_tasks_once()
            time.sleep(60)

    _thread = threading.Thread(target=loop, name="jobsync-scheduler", daemon=True)
    _thread.start()


def stop_scheduler() -> None:
    _stop_event.set()


def start_scheduler_if_enabled() -> None:
    if os.getenv("RUN_JOB_SCHEDULER", "").strip().lower() in {"1", "true", "yes"}:
        start_scheduler()
