import os
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import CoverLetterRequest, CoverLetterResponse
from backend.models import UserProfile, User
from backend.security import get_current_user
from core.cover_letter_blueprint_engine import generate_cover_letter_draft
from core.pdf_generator import generate_resume_pdf

router = APIRouter(prefix="/cover-letter", tags=["Cover Letter"])

@router.post("/generate", response_model=CoverLetterResponse)
async def generate_cover_letter(req: CoverLetterRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found for cover letter generation")

    payload = await generate_cover_letter_draft(profile, req.model_dump())
    return CoverLetterResponse(draft=payload["draft"], source_ids=payload.get("source_ids", []))


@router.post("/download")
async def download_cover_letter(req: CoverLetterRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="No profile found for cover letter download")

    payload = await generate_cover_letter_draft(profile, req.model_dump())
    draft = payload["draft"]

    candidate_name = getattr(profile, "full_name", None) or getattr(current_user, "name", None) or getattr(current_user, "email", None) or "Candidate"
    contact_lines = [line for line in [getattr(profile, "email", None), getattr(profile, "phone", None), getattr(profile, "location", None)] if line]

    pdf_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            pdf_path = temp_file.name

        generate_resume_pdf(draft, pdf_path, candidate_name=candidate_name, contact_lines=contact_lines)
        with open(pdf_path, "rb") as pdf_file:
            pdf_bytes = pdf_file.read()

        filename = f"cover_letter_{(req.role or 'role').strip().replace(' ', '_').lower()}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    finally:
        if pdf_path:
            try:
                os.unlink(pdf_path)
            except Exception:
                pass
