"""
Browser Extension API - Import jobs from URLs
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.url_ingestion import extract_job_text_from_url
from core.database import get_db
from backend.models import Job

router = APIRouter(prefix="/extension", tags=["Browser Extension"])

class URLAnalyze(BaseModel):
    url: str

@router.post("/analyze-url")
def analyze_url(req: URLAnalyze, db: Session = Depends(get_db)):
    """Analyze job posting from URL"""
    job_data = extract_job_text_from_url(req.url)
    
    if not job_data.get("success"):
        return {
            "success": False,
            "error": job_data.get("error", "Failed to extract job data")
        }
    
    # Save raw job for later analysis
    new_job = Job(
        source="url_ingest",
        external_id=req.url,
        title="Imported Job",
        company="",
        location="",
        description=job_data["raw_text"],
        url=req.url
    )
    
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    
    return {
        "success": True,
        "job_id": new_job.id,
        "message": "Job saved. Go to dashboard to analyze.",
        "preview": job_data["raw_text"][:500]
    }
