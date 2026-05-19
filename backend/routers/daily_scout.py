"""
Daily Scout API - Automated job hunting
"""
from fastapi import APIRouter
from backend.schemas import ScoutRequest
from core.daily_scout import run_daily_scout, get_scout_status

router = APIRouter(prefix="/scout", tags=["Daily Scout"])

@router.post("/run")
def run_scout(req: ScoutRequest):
    """Run daily scout to find and save matching jobs"""
    result = run_daily_scout(
        role=req.role,
        location=req.location,
        skills=req.skills,
        min_score=req.min_score,
        page=req.page,
    )
    return result

@router.get("/status")
def scout_status():
    """Get daily scout status"""
    status = get_scout_status()
    status["enabled"] = True
    return status
