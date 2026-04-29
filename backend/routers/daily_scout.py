"""
Daily Scout API - Automated job hunting
"""
from fastapi import APIRouter
from pydantic import BaseModel
from core.daily_scout import run_daily_scout

router = APIRouter(prefix="/scout", tags=["Daily Scout"])

class ScoutRequest(BaseModel):
    query: str = "software engineer"
    location: str = "remote"
    min_score: int = 75

@router.post("/run")
def run_scout(req: ScoutRequest):
    """Run daily scout to find and save matching jobs"""
    result = run_daily_scout(
        query=req.query,
        location=req.location,
        min_score=req.min_score
    )
    return result

@router.get("/status")
def scout_status():
    """Get daily scout status"""
    return {
        "enabled": True,
        "last_run": None,  # TODO: Track in database
        "message": "Daily scout is ready to run"
    }
