"""
Kanban Board API - Visual application tracking
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from backend.models import Application, ApplicationStatus, UserProfile
from core.llm_provider import LLMProvider
from pydantic import BaseModel
from datetime import datetime
import json

router = APIRouter(prefix="/kanban", tags=["Kanban"])

class ApplicationMove(BaseModel):
    id: int
    new_status: str

class FollowUpRequest(BaseModel):
    id: int

def _parse_date(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except Exception:
        return None

def _urgency_for_application(app):
    now = datetime.now()
    interview_date = _parse_date(app.interview_date)
    follow_up_date = _parse_date(app.follow_up_date)

    if interview_date:
        days_until_interview = (interview_date - now).days
        if days_until_interview < 2:
            return {
                "level": "red",
                "label": "Interview soon",
                "details": f"Interview in {max(days_until_interview, 0)} day(s)",
            }

    if follow_up_date and follow_up_date < now and app.status == ApplicationStatus.APPLIED.value:
        return {
            "level": "yellow",
            "label": "Follow-up overdue",
            "details": f"Follow up was due on {follow_up_date.strftime('%b %d')}",
        }

    return {
        "level": "green",
        "label": "On track",
        "details": "No immediate action needed",
    }

def _format_date(value):
    parsed = _parse_date(value)
    if not parsed:
        return None
    return parsed.strftime('%Y-%m-%d')

@router.get("/board")
def get_board(db: Session = Depends(get_db)):
    """Get Kanban board with applications grouped by status"""
    columns = {
        ApplicationStatus.SAVED.value: [],
        ApplicationStatus.APPLIED.value: [],
        ApplicationStatus.INTERVIEWING.value: [],
        ApplicationStatus.REJECTED.value: [],
        ApplicationStatus.OFFERED.value: []
    }
    
    profile = db.query(UserProfile).first()
    latest_ats_score = profile.latest_ats_score if profile else None
    apps = db.query(Application).all()
    
    for app in apps:
        status = app.status
        if status in columns:
            columns[status].append({
                "id": app.id,
                "company": app.company,
                "role": app.role,
                "status": app.status,
                "applied_date": _format_date(app.applied_date),
                "interview_date": _format_date(app.interview_date),
                "follow_up_date": _format_date(app.follow_up_date),
                "next_action": app.next_action,
                "notes": app.notes,
                "ats_score": latest_ats_score,
                "urgency": _urgency_for_application(app),
            })
    
    return columns

@router.post("/move")
def move_application(move: ApplicationMove, db: Session = Depends(get_db)):
    """Move application to different status column"""
    app = db.query(Application).filter(Application.id == move.id).first()
    
    if not app:
        raise HTTPException(404, "Application not found")
    
    # Validate new status
    allowed = {s.value for s in ApplicationStatus}
    if move.new_status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid status")

    app.status = move.new_status
    db.commit()
    
    return {"success": True, "message": f"Moved to {move.new_status}"}

@router.post("/follow-up-email")
def generate_follow_up_email(req: FollowUpRequest, db: Session = Depends(get_db)):
    """Generate a follow-up email draft for an application."""
    app = db.query(Application).filter(Application.id == req.id).first()

    if not app:
        raise HTTPException(404, "Application not found")

    llm = LLMProvider()
    prompt = f"""Write a concise, professional follow-up email.

Company: {app.company}
Role: {app.role}
Applied date: {_format_date(app.applied_date) or 'unknown'}
Interview date: {_format_date(app.interview_date) or 'none'}
Current status: {app.status}
Notes: {app.notes or 'none'}

Return plain text only with:
Subject line
Email body

Tone: friendly, polished, and direct.
"""

    draft = llm.ask("You are a professional job seeker writing a follow-up email.", prompt)
    if not draft or draft.startswith("AI error"):
        draft = f"Subject: Following up on the {app.role} role\n\nHi {app.company} team,\n\nI hope you're doing well. I wanted to follow up on my application for the {app.role} position and reiterate my interest in the opportunity. Please let me know if there's any additional information I can provide.\n\nBest regards,\n[Your Name]"

    return {
        "success": True,
        "draft": draft,
        "company": app.company,
        "role": app.role,
    }
