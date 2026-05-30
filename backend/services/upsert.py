from __future__ import annotations

from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.models import Job
from core.deduplicator import process_incoming_job


def upsert_job(db: Session, raw_job: Dict[str, Any]) -> Job:
    """Upsert a job record using the shared deduplicator logic.

    University-related upsert functions have been removed as part of
    the university module deprecation.
    """
    job, action = process_incoming_job(db, raw_job)
    return job
