from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import CoverLetterRequest, CoverLetterResponse
from core.llm_provider import LLMProvider
from backend.models import UserProfile

router = APIRouter(prefix="/cover-letter", tags=["Cover Letter"])

@router.post("/generate", response_model=CoverLetterResponse)
def generate_cover_letter(req: CoverLetterRequest, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).first()
    resume_context = ""
    if profile and profile.resume_text:
        resume_context = f"Resume: {profile.resume_text[:1500]}"

    tone = (req.tone or "professional").strip().lower()
    tone_guidance = {
        "professional": "Use a polished, confident professional tone.",
        "warm": "Use a warm, approachable tone while staying credible.",
        "bold": "Use a direct, high-energy tone that sounds ambitious.",
        "concise": "Keep the letter tight, crisp, and efficient.",
    }.get(tone, "Use a polished, confident professional tone.")

    prompt = f"""Write a tailored cover letter for the following job at {req.company} for the role {req.role}.
Tone: {tone}
Guidance: {tone_guidance}
Job description: {req.job_description[:2000]}
{resume_context}
Make it personal, specific, and highlight relevant skills. End with a short call to action. Keep under 320 words."""

    llm = LLMProvider()
    draft = llm.ask("You are a helpful career AI assistant.", prompt)
    if not draft:
        draft = "[AI unavailable] Please provide more job details to generate a cover letter."
    return CoverLetterResponse(draft=draft)
