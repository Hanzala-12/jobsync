"""
Browser Extension API - Import jobs from URLs
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from core.url_ingestion import extract_job_text_from_url
from core.database import get_db
from core.deduplicator import process_incoming_job
from core.normalizer import normalize_job

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
    
    normalized = normalize_job(
        {
            "title": "Imported Job",
            "company": "Unknown",
            "city": "",
            "location": "",
            "description": job_data["raw_text"],
            "apply_url": req.url,
            "url": req.url,
            "external_id": req.url,
        },
        "url_ingest",
    )
    new_job, _ = process_incoming_job(db, normalized)
    
    return {
        "success": True,
        "job_id": new_job.id,
        "message": "Job saved. Go to dashboard to analyze.",
        "preview": job_data["raw_text"][:500]
    }
