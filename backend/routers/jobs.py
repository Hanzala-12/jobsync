from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Job
from backend.services.job_apis import fetch_all_jobs
from backend.schemas import JobOut, JobMatch
from core.llm_provider import LLMProvider
from backend.models import UserProfile
from core.job_search import search_jobs_jsearch
from typing import List, Optional

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/search", response_model=List[JobOut])
def search_jobs(
    query: str = "software developer", 
    location: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Search jobs with optional location filter.
    Location format: "City, Country" or just "Country" (e.g., "Lahore, Pakistan")
    """
    # If location is provided, use JSearch API with location validation
    if location:
        raw_jobs = search_jobs_jsearch(query, location_raw=location)
        saved = []
        for j in raw_jobs:
            if not j.get("id"):
                continue
            ext_id = str(j.get("id"))
            existing = db.query(Job).filter(Job.external_id == ext_id).first()

            if not existing:
                title = (j.get("title") or "").strip()
                company = (j.get("company") or "").strip()
                if title and company:
                    existing = db.query(Job).filter(
                        Job.title.ilike(title),
                        Job.company.ilike(company)
                    ).first()

            if not existing:
                new_job = Job(
                    source="jsearch",
                    external_id=ext_id,
                    title=j["title"],
                    company=j["company"],
                    location=j["location"],
                    description=j["description"],
                    url=j["url"],
                    posted_date=j.get("posted")
                )
                db.add(new_job)
                db.commit()
                db.refresh(new_job)
                saved.append(new_job)
            else:
                saved.append(existing)
        return saved
    else:
        # Fallback to existing job APIs
        raw_jobs = fetch_all_jobs(query)
        saved = []
        for j in raw_jobs:
            ext = j.get("external_id")
            existing = None
            if ext:
                existing = db.query(Job).filter(Job.external_id == ext).first()

            if not existing:
                title = (j.get("title") or "").strip()
                company = (j.get("company") or "").strip()
                if title and company:
                    existing = db.query(Job).filter(
                        Job.title.ilike(title),
                        Job.company.ilike(company)
                    ).first()

            if not existing:
                new_job = Job(
                    source=j["source"],
                    external_id=j.get("external_id"),
                    title=j["title"],
                    company=j["company"],
                    location=j["location"],
                    description=j["description"],
                    url=j["url"],
                    posted_date=j["posted_date"]
                )
                db.add(new_job)
                db.commit()
                db.refresh(new_job)
                saved.append(new_job)
            else:
                saved.append(existing)
        return saved

@router.get("/{job_id}/match", response_model=JobMatch)
def match_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JobMatch(job_id=job_id, match_percentage=0, explanation="Job not found", missing_skills=[])
    profile = db.query(UserProfile).first()
    if not profile or not profile.resume_text:
        return JobMatch(job_id=job_id, match_percentage=0, explanation="Upload resume first", missing_skills=[])

    prompt = f"""Compare the resume with the job description.
Resume: {profile.resume_text[:2000]}
Job Description: {job.description[:2000]}
Give:
- Match percentage (0-100)
- Explanation (why this score)
- List missing skills
Respond as JSON: {{"percentage": number, "explanation": "string", "missing_skills": ["..."]}}"""

    llm = LLMProvider()
    response = llm.ask("You are a hiring expert.", prompt)
    import json
    try:
        data = json.loads(response)
        return JobMatch(
            job_id=job_id,
            match_percentage=data.get("percentage", 0),
            explanation=data.get("explanation", ""),
            missing_skills=data.get("missing_skills", [])
        )
    except Exception:
        return JobMatch(job_id=job_id, match_percentage=0, explanation="Failed to parse AI response", missing_skills=[])
