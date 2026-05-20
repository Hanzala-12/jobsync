"""
Follow-up Agent - Automated follow-up reminders and drafts
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from backend.models import Application, ApplicationStatus
from core.llm_provider import LLMProvider
from datetime import datetime, timedelta

router = APIRouter(prefix="/followup", tags=["Follow-Up"])

@router.get("/check")
def check_followups(db: Session = Depends(get_db)):
    """Check for stale applications and generate follow-up drafts"""
    cutoff = datetime.now() - timedelta(days=5)
    
    # Find applications that need follow-up
    stale_apps = db.query(Application).filter(
        Application.status == ApplicationStatus.APPLIED.value,
        Application.applied_date <= cutoff
    ).all()
    
    llm = LLMProvider()
    followups = []
    
    for app in stale_apps:
        # Generate follow-up email draft
        prompt = f"""Write a professional follow-up email for a job application.

Company: {app.company}
Role: {app.role}
Applied: {app.applied_date}
Days since application: {(datetime.now() - app.applied_date).days}

Include:
- Subject line
- Polite inquiry about application status
- Reiterate interest
- Professional closing

Keep it concise and professional."""
        
        draft = llm.ask("You are a professional job seeker.", prompt)
        
        followups.append({
            "app_id": app.id,
            "company": app.company,
            "role": app.role,
            "applied_date": str(app.applied_date),
            "days_since": (datetime.now() - app.applied_date).days,
            "draft": draft
        })
    
    return {
        "count": len(followups),
        "followups": followups
    }

@router.post("/send/{app_id}")
def mark_followup_sent(app_id: int, db: Session = Depends(get_db)):
    """Mark follow-up as sent and update application"""
    app = db.query(Application).filter(Application.id == app_id).first()
    
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    
    app.follow_up_date = datetime.now()
    app.next_action = "Wait for response"
    db.commit()
    
    return {"success": True, "message": "Follow-up marked as sent"}
