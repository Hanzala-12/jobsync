from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import CoverLetterRequest, CoverLetterResponse
from backend.models import UserProfile
from core.rag_service import generate_cover_letter_with_rag_async, save_cover_letter_artifacts

router = APIRouter(prefix="/cover-letter", tags=["Cover Letter"])

@router.post("/generate", response_model=CoverLetterResponse)
async def generate_cover_letter(req: CoverLetterRequest, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).first()
    resume_context = ""
    if profile and profile.resume_text:
        resume_context = profile.resume_text[:1500]

    tone = (req.tone or "professional").strip().lower()
    tone_guidance = {
        "professional": "Use a polished, confident professional tone.",
        "warm": "Use a warm, approachable tone while staying credible.",
        "bold": "Use a direct, high-energy tone that sounds ambitious.",
        "concise": "Keep the letter tight, crisp, and efficient.",
    }.get(tone, "Use a polished, confident professional tone.")

    draft, source_ids, retrieved_chunks = await generate_cover_letter_with_rag_async(
        req.job_description,
        resume_context or req.job_description[:500],
        company_name=req.company,
        role=req.role,
        tone=tone,
        top_k=5,
    )
    save_cover_letter_artifacts(
        None,
        draft,
        source_ids,
        retrieved_chunks,
        metadata={"company": req.company, "role": req.role, "tone": tone, "guidance": tone_guidance},
    )
    return CoverLetterResponse(draft=draft, source_ids=source_ids)
