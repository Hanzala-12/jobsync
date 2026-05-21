from __future__ import annotations

from typing import Dict, Any
from sqlalchemy.orm import Session
from backend.models import Job, University
from core.deduplicator import process_incoming_job


def upsert_job(db: Session, raw_job: Dict[str, Any]) -> Job:
    # Reuse existing deduplicator to merge or create jobs safely
    job, action = process_incoming_job(db, raw_job)
    return job


def upsert_university(db: Session, payload: Dict[str, Any]) -> University:
    # Prefer external_id/source if provided
    external = payload.get("external_id") or payload.get("source_id")
    if external:
        u = db.query(University).filter(University.id == external).first()
        if u:
            # simple merge
            for k, v in payload.items():
                if hasattr(u, k) and v is not None:
                    setattr(u, k, v)
            db.commit()
            db.refresh(u)
            return u
    # fallback to name + country
    name = (payload.get("name") or "").strip()
    country = (payload.get("country") or "").strip()
    if name and country:
        u = db.query(University).filter(University.name == name, University.country == country).first()
        if u:
            for k, v in payload.items():
                if hasattr(u, k) and v is not None:
                    setattr(u, k, v)
            db.commit()
            db.refresh(u)
            return u
    # create new
    u = University(**{k: v for k, v in payload.items() if hasattr(University, k)})
    db.add(u)
    db.commit()
    db.refresh(u)
    return u
