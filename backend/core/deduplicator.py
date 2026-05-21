from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from typing import Dict, Iterable, Optional, Tuple

from rapidfuzz import fuzz
from sqlalchemy.orm import Session

from backend.models import Job
from backend.config.pakistan_jobs_config import SOURCE_PRIORITY


def generate_fingerprint(title, company, city):
    title = (title or "").lower().strip()
    company = (company or "").lower().strip()
    city = (city or "").lower().strip()

    for suffix in [" pvt ltd", " (pvt) ltd", " pvt. ltd.", " limited", " ltd", " inc", " llc", " pakistan", " pk"]:
        company = company.replace(suffix, "")
    company = company.strip()

    for prefix in ["senior ", "sr. ", "sr ", "junior ", "jr. ", "jr ", "lead ", "principal ", "associate ", "staff "]:
        title = title.replace(prefix, "")

    title = re.sub(r"[^\w\s]", "", title)
    company = re.sub(r"[^\w\s]", "", company)
    title = re.sub(r"\s+", " ", title).strip()
    company = re.sub(r"\s+", " ", company).strip()

    composite = f"{title}|{company}|{city}"
    return hashlib.md5(composite.encode()).hexdigest()


def is_fuzzy_duplicate(new_job: Dict, candidate_jobs: Iterable[Job]) -> Tuple[bool, Optional[Job]]:
    for existing in candidate_jobs:
        title_score = fuzz.token_sort_ratio(new_job["title"].lower(), (existing.title or "").lower())
        company_score = fuzz.token_sort_ratio(new_job["company"].lower(), (existing.company or "").lower())
        combined = (title_score * 0.65) + (company_score * 0.35)

        if title_score >= 85 and company_score >= 80:
            return True, existing
        if title_score >= 92 and combined >= 75:
            return True, existing

    return False, None


def is_description_duplicate(new_job: Dict, candidate_jobs: Iterable[Job]) -> Tuple[bool, Optional[Job]]:
    if not new_job.get("description"):
        return False, None

    new_desc = new_job["description"][:500].lower()
    for existing in candidate_jobs:
        if not existing.description:
            continue
        existing_desc = existing.description[:500].lower()
        desc_score = fuzz.ratio(new_desc, existing_desc)
        if desc_score >= 88:
            return True, existing

    return False, None


def _read_sources_seen(existing_job: Job) -> list:
    if not existing_job.sources_seen:
        return [existing_job.source] if existing_job.source else []
    try:
        parsed = json.loads(existing_job.sources_seen)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        return [item.strip() for item in str(existing_job.sources_seen).split(",") if item.strip()]


def handle_duplicate(db: Session, new_job: Dict, existing_job: Job, source_priority=None) -> Job:
    source_priority = source_priority or SOURCE_PRIORITY
    new_priority = source_priority.get(new_job.get("source"), 99)
    existing_priority = source_priority.get(existing_job.source, 99)
    sources_seen = _read_sources_seen(existing_job)

    if new_job.get("source") and new_job["source"] not in sources_seen:
        sources_seen.append(new_job["source"])
        existing_job.sources_seen = json.dumps(sources_seen)

    if new_priority < existing_priority:
        existing_job.apply_url = new_job.get("apply_url") or new_job.get("url") or existing_job.apply_url
        existing_job.url = new_job.get("url") or new_job.get("apply_url") or existing_job.url
        existing_job.source = new_job.get("source") or existing_job.source

    if new_job.get("description") and len(new_job["description"]) > len(existing_job.description or ""):
        existing_job.description = new_job["description"]

    if not existing_job.salary and new_job.get("salary"):
        existing_job.salary = new_job["salary"]

    if new_job.get("location"):
        existing_job.location = new_job["location"]

    if new_job.get("city"):
        existing_job.city = new_job["city"]

    if new_job.get("apply_url") or new_job.get("url"):
        existing_job.apply_url = new_job.get("apply_url") or existing_job.apply_url
        existing_job.url = new_job.get("url") or new_job.get("apply_url") or existing_job.url

    existing_job.last_seen_at = datetime.now()
    existing_job.possibly_inactive = bool(new_job.get("possibly_inactive", existing_job.possibly_inactive))
    db.commit()
    db.refresh(existing_job)
    return existing_job


def _candidate_jobs(db: Session, city: str) -> list[Job]:
    cutoff = datetime.now() - timedelta(days=60)
    query = db.query(Job).filter(Job.city == city)
    candidates = []
    for job in query.all():
        parsed = _parse_existing_posted_date(job.posted_date)
        if parsed is None or parsed >= cutoff:
            candidates.append(job)
    return candidates


def _parse_existing_posted_date(value) -> Optional[datetime]:
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


def process_incoming_job(db: Session, new_job: Dict) -> Tuple[Job, str]:
    fingerprint = generate_fingerprint(new_job["title"], new_job["company"], new_job.get("city", ""))

    external_id = str(new_job.get("external_id") or new_job.get("apply_url") or "").strip()
    if external_id:
        external_match = db.query(Job).filter(Job.external_id == external_id).first()
        if external_match:
            return handle_duplicate(db, new_job, external_match, SOURCE_PRIORITY), "external_id"

    exact_match = db.query(Job).filter(Job.dedup_fingerprint == fingerprint).first()
    if exact_match:
        return handle_duplicate(db, new_job, exact_match, SOURCE_PRIORITY), "layer1"

    candidates = _candidate_jobs(db, new_job.get("city", ""))
    is_dup, matched = is_fuzzy_duplicate(new_job, candidates)
    if is_dup and matched:
        return handle_duplicate(db, new_job, matched, SOURCE_PRIORITY), "layer2"

    if new_job.get("description"):
        is_dup, matched = is_description_duplicate(new_job, candidates)
        if is_dup and matched:
            return handle_duplicate(db, new_job, matched, SOURCE_PRIORITY), "layer3"

    now = datetime.now()
    job = Job(
        source=new_job.get("source"),
        external_id=external_id or None,
        title=new_job.get("title", ""),
        company=new_job.get("company", ""),
        location=new_job.get("location") or new_job.get("city") or "",
        city=new_job.get("city", ""),
        description=new_job.get("description", ""),
        url=new_job.get("url") or new_job.get("apply_url") or "",
        apply_url=new_job.get("apply_url") or new_job.get("url") or "",
        posted_date=str(new_job.get("posted_date") or ""),
        salary=new_job.get("salary") or "",
        job_type=new_job.get("job_type"),
        experience_required=new_job.get("experience_required"),
        scraped_at=new_job.get("scraped_at") or now,
        dedup_fingerprint=fingerprint,
        sources_seen=json.dumps([new_job.get("source")]),
        first_seen_at=now,
        last_seen_at=now,
        possibly_inactive=bool(new_job.get("possibly_inactive", False)),
        is_active=True,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job, "created"


def daily_dedup_cleanup(db: Session) -> Dict[str, int]:
    cutoff = datetime.now() - timedelta(days=7)
    recent = []
    for job in db.query(Job).filter(Job.is_active == True).all():  # noqa: E712
        first_seen = job.first_seen_at or _parse_existing_posted_date(job.posted_date)
        if first_seen is None or first_seen >= cutoff:
            recent.append(job)

    merged = 0
    for index, job in enumerate(recent):
        if not job.is_active:
            continue
        candidates = recent[index + 1 :]
        new_job = {
            "title": job.title or "",
            "company": job.company or "",
            "city": job.city or "",
            "description": job.description or "",
            "source": job.source or "",
            "apply_url": job.apply_url or job.url or "",
            "salary": job.salary or "",
        }
        is_dup, matched = is_fuzzy_duplicate(new_job, candidates)
        if not is_dup:
            is_dup, matched = is_description_duplicate(new_job, candidates)
        if is_dup and matched:
            handle_duplicate(db, new_job, matched, SOURCE_PRIORITY)
            job.is_active = False
            job.possibly_inactive = True
            merged += 1
    db.commit()
    return {"merged": merged, "checked": len(recent)}
