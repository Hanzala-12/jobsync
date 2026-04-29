"""
Daily Scout - Automated job hunting background task
"""
from datetime import datetime
from core.job_search import search_jobs_jsearch
from core.engine import JobAnalyser
from core.llm_provider import LLMProvider
from core.database import get_db
from backend.models import UserProfile, Job, Application

def run_daily_scout(query="software engineer", location="remote", min_score=75) -> dict:
    """
    Fetches live jobs, scores against user's resume, saves top matches
    Returns summary of found and saved jobs
    """
    db = next(get_db())
    
    try:
        # Get user's resume
        profile = db.query(UserProfile).first()
        if not profile or not profile.resume_text:
            return {"error": "No resume found. Upload resume first."}
        
        # Initialize AI components
        llm = LLMProvider()
        analyser = JobAnalyser(llm)
        
        # Analyze resume once
        resume_analysis = analyser.analyse_resume(profile.resume_text)
        
        # Fetch jobs from JSearch
        jobs = search_jobs_jsearch(query, location)
        
        if not jobs:
            return {"error": "No jobs found. Check API key or try different query."}
        
        # Score and filter jobs
        matches = analyser.score_and_filter_jobs(resume_analysis, jobs, min_score)
        
        # Save to database
        saved_ids = []
        for job in matches:
            # Check if already exists
            existing = db.query(Job).filter(Job.external_id == str(job["id"])).first()
            if not existing:
                new_job = Job(
                    source="jsearch",
                    external_id=str(job["id"]),
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
        
        return {
            "success": True,
            "found": len(matches),
            "saved": len(saved_ids),
            "top_jobs": [{"title": j["title"], "company": j["company"], "score": j["match_score"]} for j in matches[:5]]
        }
    
    except Exception as e:
        return {"error": str(e)}
    finally:
        db.close()
