"""
Daily Scout - Automated job hunting background task
"""
from datetime import datetime
from typing import Any, Dict
from core.job_search import search_jobs_jsearch
from core.engine import JobAnalyser
from core.llm_provider import LLMProvider
from core.database import get_db
from backend.models import UserProfile, Job, Application


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

def run_daily_scout(query="software engineer", location="remote", min_score=75) -> dict:
    """
    Fetches live jobs, scores against user's resume, saves top matches
    Returns summary of found and saved jobs
    """
    db = next(get_db())
    
    try:
        _set_state(running=True, progress=5, message="Loading resume", error=None, results=[])
        # Get user's resume
        profile = db.query(UserProfile).first()
        if not profile or not profile.resume_text:
            _set_state(running=False, progress=100, message="Resume missing", error="No resume found. Upload resume first.")
            return {"error": "No resume found. Upload resume first."}
        
        # Initialize AI components
        llm = LLMProvider()
        analyser = JobAnalyser(llm)
        
        # Analyze resume once
        resume_analysis = analyser.analyse_resume(profile.resume_text)
        _set_state(progress=20, message="Resume analyzed")
        
        # Fetch jobs from JSearch with location_raw parameter
        _set_state(progress=35, message="Searching live jobs")
        jobs = search_jobs_jsearch(query, location_raw=location)
        
        if not jobs:
            _set_state(running=False, progress=100, message="No jobs found", error="No jobs found. Check API key or try different query.")
            return {"error": "No jobs found. Check API key or try different query."}
        
        # Score and filter jobs
        _set_state(progress=55, message="Scoring jobs against resume")
        matches = analyser.score_and_filter_jobs(resume_analysis, jobs, min_score)
        
        # Save to database
        saved_ids = []
        duplicate_count = 0
        for job in matches:
            # Check if already exists by external_id when available
            ext_id = str(job.get("id")) if job.get("id") is not None else None
            existing = None
            if ext_id:
                existing = db.query(Job).filter(Job.external_id == ext_id).first()

            # If no external_id match, try matching by title + company (case-insensitive)
            if not existing:
                title = (job.get("title") or "").strip()
                company = (job.get("company") or "").strip()
                if title and company:
                    existing = db.query(Job).filter(
                        Job.title.ilike(title),
                        Job.company.ilike(company)
                    ).first()

            if not existing:
                new_job = Job(
                    source="jsearch",
                    external_id=ext_id,
                    title=job["title"],
                    company=job["company"],
                    location=job["location"],
                    description=job["description"],
                    url=job["url"],
                    posted_date=job.get("posted")
                )
                db.add(new_job)
                db.commit()
                db.refresh(new_job)
                saved_ids.append(new_job.id)
            else:
                duplicate_count += 1

        discovered_jobs = [
            {
                "id": job.get("id"),
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "description": job.get("description"),
                "url": job.get("url"),
                "posted": job.get("posted"),
                "match_score": job.get("match_score", 0),
                "source": job.get("source", "jsearch"),
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
            "top_jobs": [{"title": j["title"], "company": j["company"], "score": j["match_score"]} for j in matches[:5]]
        }
    
    except Exception as e:
        _set_state(running=False, progress=100, message="Scout failed", error=str(e))
        return {"error": str(e)}
    finally:
        db.close()
