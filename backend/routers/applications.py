from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Application, ApplicationStatus, ResumeVersion, UserProfile
from backend.schemas import (
    ApplicationCreate,
    ApplicationOut,
    ApplicationUpdate,
    HealthScoreResponse,
    StatusUpdate,
)

router = APIRouter(prefix="/applications", tags=["Applications"])


def _calculate_streak(applications: List[Application]) -> int:
    if not applications:
        return 0

    dates_with_apps = {
        app.applied_date.date()
        for app in applications
        if app.applied_date is not None
    }
    if not dates_with_apps:
        return 0

    streak = 0
    cursor = datetime.utcnow().date()
    while cursor in dates_with_apps:
        streak += 1
        cursor = cursor - timedelta(days=1)

    return streak


def _grade(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    if score >= 60:
        return "D"
    return "F"


def _status_message(score: int) -> str:
    if score >= 85:
        return "Strong momentum. Keep applying consistently and follow up quickly."
    if score >= 70:
        return "Good progress with room to tighten your follow-ups and targeting."
    if score >= 55:
        return "Your pipeline needs focus this week. Add fresh applications and improve resume targeting."
    return "Recovery mode: rebuild your pipeline this week with targeted applications and follow-ups."


@router.post("/", response_model=ApplicationOut)
def create_application(app: ApplicationCreate, db: Session = Depends(get_db)):
    new_app = Application(
        job_id=app.job_id,
        company=app.company,
        role=app.role,
        source=app.source,
        status=app.status if getattr(app, "status", None) else ApplicationStatus.SAVED.value,
        next_action=app.next_action,
        notes=app.notes,
        resume_version=app.resume_version,
        contact_email=app.contact_email,
    )
    db.add(new_app)
    db.commit()
    db.refresh(new_app)
    return new_app


@router.get("/", response_model=List[ApplicationOut])
def list_applications(status: str = None, db: Session = Depends(get_db)):
    query = db.query(Application)
    if status:
        query = query.filter(Application.status == status)
    return query.order_by(Application.applied_date.desc()).all()


@router.get("/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    return app


@router.patch("/{app_id}/status", response_model=ApplicationOut)
def update_status(app_id: int, status_update: StatusUpdate, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")
    app.status = status_update.status
    db.commit()
    db.refresh(app)
    return app


@router.patch("/{app_id}", response_model=ApplicationOut)
def update_application(app_id: int, update: ApplicationUpdate, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")

    for field, value in update.model_dump(exclude_unset=True).items():
        setattr(app, field, value)

    db.commit()
    db.refresh(app)
    return app


@router.delete("/{app_id}")
def delete_application(app_id: int, db: Session = Depends(get_db)):
    app = db.query(Application).filter(Application.id == app_id).first()
    if not app:
        raise HTTPException(404, "Application not found")

    db.delete(app)
    db.commit()
    return {"success": True}


@router.get("/health-score", response_model=HealthScoreResponse)
def application_health_score(db: Session = Depends(get_db)):
    applications = db.query(Application).order_by(Application.applied_date.desc()).all()
    profile = db.query(UserProfile).first()
    resume_versions = db.query(ResumeVersion).all()

    now = datetime.utcnow()
    seven_days_ago = now - timedelta(days=7)

    total_apps = len(applications)
    recent_apps = [app for app in applications if app.applied_date and app.applied_date >= seven_days_ago]
    interview_scheduled = [
        app
        for app in applications
        if app.interview_date and app.interview_date >= now
    ]
    rejections = [app for app in applications if app.status == ApplicationStatus.REJECTED.value]

    scores = []
    if profile and profile.latest_ats_score is not None:
        scores.append(float(profile.latest_ats_score))
    scores.extend([float(v.ats_score) for v in resume_versions if v.ats_score is not None])
    avg_ats = (sum(scores) / len(scores)) if scores else None

    deductions: List[str] = []
    improvements: List[str] = []

    score = 100

    if len(recent_apps) == 0:
        score -= 20
        deductions.append("No applications submitted in the last 7 days (-20)")
        improvements.append("Submit at least 3 targeted applications this week.")

    if total_apps >= 10 and len(interview_scheduled) == 0:
        score -= 15
        deductions.append("10+ applications with zero interviews scheduled (-15)")
        improvements.append("Refine resume targeting and customize cover letters for top roles.")

    has_resume = bool(profile and profile.resume_text) or len(resume_versions) > 0
    if not has_resume:
        score -= 20
        deductions.append("No resume uploaded or saved version found (-20)")
        improvements.append("Upload your resume and run ATS analysis today.")

    if avg_ats is not None and avg_ats < 60:
        score -= 15
        deductions.append("Average ATS score is below 60 (-15)")
        improvements.append("Use Resume Rewrite to align keywords with job descriptions.")

    if total_apps > 0 and all(app.status == ApplicationStatus.SAVED.value for app in applications):
        score -= 10
        deductions.append("All applications are still in Saved status (-10)")
        improvements.append("Move at least one saved role to Applied after submitting.")

    has_followups = any((app.next_action and app.next_action.strip()) or app.follow_up_date for app in applications)
    if total_apps > 0 and not has_followups:
        score -= 10
        deductions.append("No follow-up actions are set (-10)")
        improvements.append("Add follow-up tasks for active applications.")

    if len(rejections) >= 5 and len(recent_apps) == 0:
        score -= 10
        deductions.append("5+ rejections with no new applications this week (-10)")
        improvements.append("Rebuild momentum with 3 fresh applications in your strongest niche.")

    if len(interview_scheduled) > 0:
        score += 10
        improvements.append("Interview scheduled: keep preparing with mock practice (+10)")

    if any(app.status == ApplicationStatus.OFFERED.value for app in applications):
        score += 20
        improvements.append("Offer received: negotiate confidently and keep alternatives active (+20)")

    if avg_ats is not None and avg_ats > 80:
        score += 10
        improvements.append("ATS score is above 80: resume targeting is strong (+10)")

    if len(recent_apps) >= 3:
        score += 15
        improvements.append("3+ applications submitted this week: excellent consistency (+15)")

    score = max(0, min(100, score))
    grade = _grade(score)

    return HealthScoreResponse(
        score=score,
        grade=grade,
        status_message=_status_message(score),
        deductions=deductions,
        improvements=improvements,
        streak=_calculate_streak(applications),
    )
