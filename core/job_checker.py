from __future__ import annotations

import logging
from datetime import datetime, timedelta

import requests
from fake_useragent import UserAgent
from sqlalchemy.orm import Session

from backend.models import Job

logger = logging.getLogger(__name__)

CLOSED_SIGNALS = [
    "this job is no longer available",
    "position has been filled",
    "job expired",
    "no longer accepting",
    "this position is closed",
    "vacancy closed",
]


def random_user_agent() -> str:
    try:
        return UserAgent().random
    except Exception:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def mark_inactive(db: Session, job: Job, reason: str) -> None:
    job.is_active = False
    job.possibly_inactive = True
    notes = f" inactive_reason={reason}"
    job.description = (job.description or "") + notes if notes not in (job.description or "") else job.description
    db.commit()


def check_job_still_active(db: Session, job: Job) -> str:
    """Verify a job is still live at its source URL."""
    apply_url = job.apply_url or job.url
    if not apply_url:
        job.possibly_inactive = True
        db.commit()
        return "missing_url"

    try:
        response = requests.get(apply_url, timeout=10, headers={"User-Agent": random_user_agent()})

        if response.status_code == 404:
            mark_inactive(db, job, reason="404_not_found")
            return "inactive_404"

        if response.status_code == 200:
            page_text = response.text.lower()
            if any(signal in page_text for signal in CLOSED_SIGNALS):
                mark_inactive(db, job, reason="job_closed_signal")
                return "inactive_closed_signal"

    except requests.exceptions.RequestException:
        logger.warning("Could not check job %s: %s", job.id, apply_url)
        return "request_failed"

    apply_staleness_rules(db, job)
    return "active_or_unknown"


def apply_staleness_rules(db: Session, job: Job) -> None:
    now = datetime.now()
    posted_date = _parse_dt(job.posted_date)
    last_seen_at = job.last_seen_at

    if posted_date and posted_date < now - timedelta(days=30) and not last_seen_at:
        job.possibly_inactive = True
    if posted_date and posted_date < now - timedelta(days=60):
        job.possibly_inactive = True
    if last_seen_at and last_seen_at < now - timedelta(days=7):
        job.possibly_inactive = True

    db.commit()


def check_oldest_jobs(db: Session, limit: int = 50) -> dict:
    jobs = (
        db.query(Job)
        .filter(Job.is_active == True)  # noqa: E712
        .order_by(Job.last_seen_at.asc().nullsfirst())
        .limit(limit)
        .all()
    )
    results = {}
    for job in jobs:
        status = check_job_still_active(db, job)
        results[status] = results.get(status, 0) + 1
    return {"checked": len(jobs), "results": results}


def _parse_dt(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            pass
    return None
