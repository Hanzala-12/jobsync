"""Daily Scout automated job hunting task."""

from datetime import datetime
from typing import Any, Dict

from backend.models import UserProfile
from backend.services.job_apis import search_jobs
from core.database import get_db
from core.deduplicator import process_incoming_job
from core.engine import JobAnalyser
from core.llm_provider import LLMProvider
from core.normalizer import normalize_job

SCOUT_STATE: Dict[str, Any] = {
    "running": False,
    "progress": 0,
    "message": "Idle",
    "last_run": None,
    "error": None,
    "results": [],
}


def _set_state(**updates):
    SCOUT_STATE.update(updates)


def get_scout_status() -> dict:
    return dict(SCOUT_STATE)


def run_daily_scout(role="software engineer", location="Pakistan", skills="", min_score=75, page=1) -> dict:
    """Fetch jobs, score against resume, and save top matches."""
    db = next(get_db())

    try:
        _set_state(running=True, progress=5, message="Loading resume", error=None, results=[])

        profile = db.query(UserProfile).first()
        if not profile or not profile.resume_text:
            _set_state(running=False, progress=100, message="Resume missing", error="No resume found. Upload resume first.")
            return {"error": "No resume found. Upload resume first."}

        llm = LLMProvider()
        analyser = JobAnalyser(llm)

        resume_analysis = analyser.analyse_resume(profile.resume_text)
        _set_state(progress=20, message="Resume analyzed")

        _set_state(progress=35, message="Searching live jobs")
        search_query = " ".join(part for part in [role, skills] if part and part.strip())
        remote_only = location.strip().lower() == "remote"
        jobs = search_jobs(query=search_query or role, location=location, remote_only=remote_only)

        if not jobs:
            _set_state(running=False, progress=100, message="No jobs found", error="No jobs found. Try a different query.")
            return {"error": "No jobs found. Try a different query."}

        _set_state(progress=55, message="Scoring jobs against resume")
        matches = analyser.score_and_filter_jobs(resume_analysis, jobs, min_score)

        saved_ids = []
        duplicate_count = 0

        for job in matches:
            normalized = normalize_job(
                {
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "city": job.get("city") or job.get("location") or location,
                    "location": job.get("location", ""),
                    "description": job.get("description", ""),
                    "apply_url": job.get("apply_url") or job.get("url") or "",
                    "url": job.get("url") or job.get("apply_url") or "",
                    "posted_date": job.get("posted_date", ""),
                    "salary": job.get("salary", ""),
                    "external_id": str(job.get("external_id") or job.get("url") or "").strip() or None,
                },
                job.get("source") or "daily-scout",
            )
            saved_job, action = process_incoming_job(db, normalized)
            if action != "created":
                duplicate_count += 1
            else:
                saved_ids.append(saved_job.id)

        discovered_jobs = [
            {
                "id": job.get("external_id") or job.get("id"),
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "description": job.get("description"),
                "url": job.get("url"),
                "posted": job.get("posted_date"),
                "match_score": job.get("match_score", 0),
                "source": job.get("source", "daily-scout"),
                "missing_skills": job.get("missing_skills", []),
            }
            for job in matches
        ]

        _set_state(
            running=False,
            progress=100,
            message="Scout complete",
            last_run=datetime.now().isoformat(),
            results=discovered_jobs,
            error=None,
        )

        return {
            "success": True,
            "found": len(matches),
            "saved": len(saved_ids),
            "duplicates_skipped": duplicate_count,
            "discovered_jobs": discovered_jobs,
            "top_jobs": [
                {"title": item["title"], "company": item["company"], "score": item["match_score"]}
                for item in discovered_jobs[:5]
            ],
        }

    except Exception as exc:
        _set_state(running=False, progress=100, message="Scout failed", error=str(exc))
        return {"error": str(exc)}
    finally:
        db.close()
