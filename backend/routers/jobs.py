from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Job
from backend.services.job_apis import fetch_all_jobs
from backend.schemas import JobOut, JobMatch
from backend.services.ai_client import ask_llm
from backend.models import UserProfile
from typing import List

router = APIRouter(prefix="/jobs", tags=["Jobs"])

@router.get("/search", response_model=List[JobOut])
def search_jobs(query: str = "software developer", db: Session = Depends(get_db)):
    # Fetch from APIs and store in DB
    raw_jobs = fetch_all_jobs(query)
    saved = []
    for j in raw_jobs:
        existing = db.query(Job).filter(Job.external_id == j["external_id"]).first()
        if not existing:
            new_job = Job(
                source=j["source"],
                external_id=j["external_id"],
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

    response = ask_llm(prompt)
    import json
    try:
        data = json.loads(response)
        return JobMatch(
            job_id=job_id,
            match_percentage=data["percentage"],
            explanation=data["explanation"],
            missing_skills=data["missing_skills"]
        )
    except:
        return JobMatch(job_id=job_id, match_percentage=0, explanation="Failed to parse AI response", missing_skills=[])
