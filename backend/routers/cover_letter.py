from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import CoverLetterRequest, CoverLetterResponse
from backend.services.ai_client import ask_llm
from backend.models import UserProfile

router = APIRouter(prefix="/cover-letter", tags=["Cover Letter"])

@router.post("/generate", response_model=CoverLetterResponse)
def generate_cover_letter(req: CoverLetterRequest, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).first()
    resume_context = ""
    if profile and profile.resume_text:
        resume_context = f"Resume: {profile.resume_text[:1500]}"

    prompt = f"""Write a tailored cover letter for the following job at {req.company} for the role {req.role}.
Job description: {req.job_description[:2000]}
{resume_context}
Make it professional, personal, and highlight relevant skills. Keep under 300 words."""

    draft = ask_llm(prompt)
    return CoverLetterResponse(draft=draft)
