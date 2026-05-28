from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import CoverLetterRequest, CoverLetterResponse
from backend.models import UserProfile, User
from backend.security import get_current_user
from backend.services.profile_data import build_profile_resume_text

router = APIRouter(prefix="/cover-letter", tags=["Cover Letter"])

@router.post("/generate", response_model=CoverLetterResponse)
async def generate_cover_letter(req: CoverLetterRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        from core.rag_service import generate_cover_letter_with_rag_async, save_cover_letter_artifacts
    except Exception as exc:
        # Keep API bootable even when optional RAG dependencies are unavailable.
        raise HTTPException(status_code=503, detail="Cover letter generation dependencies are unavailable") from exc

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    resume_context = ""
    if profile and profile.resume_text:
        resume_context = profile.resume_text[:1500]
    elif profile:
        resume_context = build_profile_resume_text(profile)[:1500]

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
