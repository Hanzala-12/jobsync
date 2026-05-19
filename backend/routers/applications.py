from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import Application, ApplicationStatus
from backend.schemas import ApplicationCreate, ApplicationOut, StatusUpdate
from typing import List

router = APIRouter(prefix="/applications", tags=["Applications"])

@router.post("/", response_model=ApplicationOut)
def create_application(app: ApplicationCreate, db: Session = Depends(get_db)):
    new_app = Application(
        job_id=app.job_id,
        company=app.company,
        role=app.role,
        source=app.source,
        status=app.status if getattr(app, 'status', None) else ApplicationStatus.SAVED.value,
        notes=app.notes,
        resume_version=app.resume_version,
        contact_email=app.contact_email
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
