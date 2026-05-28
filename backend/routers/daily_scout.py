"""
Daily Scout API - Automated job hunting
"""
from fastapi import APIRouter, Depends
from backend.schemas import ScoutRequest
from core.daily_scout import run_daily_scout, get_scout_status
from backend.security import get_current_user

from backend.models import User

router = APIRouter(prefix="/scout", tags=["Daily Scout"])

@router.post("/run")
def run_scout(req: ScoutRequest, current_user: User = Depends(get_current_user)):
    """Run daily scout to find and save matching jobs"""
    result = run_daily_scout(
        role=req.role,
        location=req.location,
        skills=req.skills,
        min_score=req.min_score,
        page=req.page,
        user_id=current_user.id,
    )
    return result

@router.get("/status")
def scout_status():
    """Get daily scout status"""
    status = get_scout_status()
    status["enabled"] = True
    return status
