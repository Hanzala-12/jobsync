"""
Kanban Board API - Visual application tracking
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from backend.models import Application
from pydantic import BaseModel

router = APIRouter(prefix="/kanban", tags=["Kanban"])

class ApplicationMove(BaseModel):
    id: int
    new_status: str

@router.get("/board")
def get_board(db: Session = Depends(get_db)):
    """Get Kanban board with applications grouped by status"""
    columns = {
        "Saved": [],
        "Applied": [],
        "Interviewing": [],
        "Rejected": [],
        "Offered": []
    }
    
    apps = db.query(Application).all()
    
    for app in apps:
        status = app.status
        if status in columns:
            columns[status].append({
                "id": app.id,
                "company": app.company,
                "role": app.role,
                "status": app.status,
                "applied_date": str(app.applied_date) if app.applied_date else None,
                "interview_date": str(app.interview_date) if app.interview_date else None,
                "follow_up_date": str(app.follow_up_date) if app.follow_up_date else None,
                "next_action": app.next_action,
                "notes": app.notes
            })
    
    return columns

@router.post("/move")
def move_application(move: ApplicationMove, db: Session = Depends(get_db)):
    """Move application to different status column"""
    app = db.query(Application).filter(Application.id == move.id).first()
    
    if not app:
        raise HTTPException(404, "Application not found")
    
    app.status = move.new_status
    db.commit()
    
    return {"success": True, "message": f"Moved to {move.new_status}"}
