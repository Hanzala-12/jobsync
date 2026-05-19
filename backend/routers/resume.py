import json
import tempfile
from typing import Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ResumeVersion, UserProfile
from backend.schemas import (
    ResumeAnalysis,
    ResumeReanalysisRequest,
    ResumeRewriteRequest,
    ResumeRewriteResponse,
    ResumeVersionCreate,
    ResumeVersionOut,
    ResumeVersionUpdateUsedFor,
)
from backend.services.pdf_parser import extract_text_from_pdf
from core.llm_provider import LLMProvider

router = APIRouter(prefix="/resume", tags=["Resume"])


def _extract_json(response: str, fallback: Dict):
    if not response:
        return fallback

    raw = response.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass

    if "```" in raw:
        parts = [part.strip() for part in raw.split("```") if part.strip()]
        for part in parts:
            cleaned = part.replace("json", "", 1).strip()
            try:
                return json.loads(cleaned)
            except Exception:
                continue

    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except Exception:
            pass

    return fallback


@router.post("/analyze", response_model=ResumeAnalysis)
async def analyze_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    text = extract_text_from_pdf(tmp_path)

    prompt = f"""Analyze this resume text for a tech job. Give:
1. ATS score (0-100)
2. Matched skills (list)
3. Missing important keywords (list)
4. Three specific improvement tips
Resume: {text[:3000]}
Respond in JSON format: {{"score": number, "matched_skills": ["..."], "keywords": ["..."], "tips": ["..."]}}"""

    llm = LLMProvider()
    parsed = _extract_json(
        llm.ask("You are a helpful career AI assistant.", prompt),
        {"score": 50, "matched_skills": [], "keywords": [], "tips": ["Add more role-specific keywords."]},
    )

    score = float(parsed.get("score", 50))
    matched_skills = parsed.get("matched_skills", []) or []
    keywords = parsed.get("keywords", []) or []
    tips = parsed.get("tips", []) or []

    profile = db.query(UserProfile).first()
    if not profile:
        profile = UserProfile()
        db.add(profile)

    profile.resume_text = text
    profile.skills = ", ".join(keywords) if keywords else ""
    profile.latest_ats_score = score
    db.commit()

    return ResumeAnalysis(
        ats_score=score,
        matched_skills=matched_skills,
        missing_keywords=keywords,
        tips=tips,
        resume_text=text,
    )


@router.post("/reanalyze", response_model=ResumeAnalysis)
def reanalyze_resume(req: ResumeReanalysisRequest, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).first()
    if not profile or not profile.resume_text:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    prompt = f"""Compare this resume to the job description and return JSON only.

Resume:
{profile.resume_text[:3000]}

Job Description:
{req.job_description[:3000]}

Return exactly this JSON schema:
{{
  "score": number,
  "matched_skills": ["skill1", "skill2"],
  "missing_keywords": ["skill3", "skill4"],
  "tips": ["tip1", "tip2", "tip3"]
}}"""

    llm = LLMProvider()
    parsed = _extract_json(
        llm.ask("You are a strict ATS resume analyzer.", prompt),
        {
            "score": 50,
            "matched_skills": [],
            "missing_keywords": ["Could not parse"],
            "tips": ["Try re-running the analysis against the job description."],
        },
    )

    score = float(parsed.get("score", 50))
    matched_skills = parsed.get("matched_skills", []) or []
    missing_keywords = parsed.get("missing_keywords", []) or []
    tips = parsed.get("tips", []) or []

    profile.latest_ats_score = score
    profile.skills = ", ".join(matched_skills) if matched_skills else profile.skills
    db.commit()

    return ResumeAnalysis(
        ats_score=score,
        matched_skills=matched_skills,
        missing_keywords=missing_keywords,
        tips=tips,
        resume_text=profile.resume_text,
    )


@router.post("/rewrite", response_model=ResumeRewriteResponse)
def rewrite_resume(req: ResumeRewriteRequest):
    llm = LLMProvider()
    prompt = f"""You are an expert resume writer. Rewrite this resume to match the job description.
Rules:
- Never invent experience or education
- Reorder bullets to match job priorities
- Replace generic words with job keywords
- Strengthen bullets with action verbs
- Match skills section to job requirements
- Keep same structure, optimize every line
Job Type: {req.job_type}
Job Description: {req.job_description}
Original Resume: {req.resume_text}
Return JSON only:
{{"rewritten": "...", "changes_made": [], "keywords_added": [], "keywords_removed": []}}"""

    parsed = _extract_json(
        llm.ask("You are a precise resume optimization assistant.", prompt),
        {
            "rewritten": req.resume_text,
            "changes_made": ["AI output unavailable; returned original resume text."],
            "keywords_added": [],
            "keywords_removed": [],
        },
    )

    return ResumeRewriteResponse(
        rewritten=str(parsed.get("rewritten", req.resume_text)),
        changes_made=[str(item) for item in (parsed.get("changes_made") or [])],
        keywords_added=[str(item) for item in (parsed.get("keywords_added") or [])],
        keywords_removed=[str(item) for item in (parsed.get("keywords_removed") or [])],
    )


@router.post("/versions", response_model=ResumeVersionOut)
def create_resume_version(payload: ResumeVersionCreate, db: Session = Depends(get_db)):
    version = ResumeVersion(
        name=payload.name,
        job_type=payload.job_type,
        content=payload.content,
        used_for=payload.used_for,
        ats_score=payload.ats_score,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.get("/versions", response_model=list[ResumeVersionOut])
def list_resume_versions(db: Session = Depends(get_db)):
    return db.query(ResumeVersion).order_by(ResumeVersion.created_at.desc()).all()


@router.get("/versions/{version_id}", response_model=ResumeVersionOut)
def get_resume_version(version_id: int, db: Session = Depends(get_db)):
    version = db.query(ResumeVersion).filter(ResumeVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Resume version not found")
    return version


@router.delete("/versions/{version_id}")
def delete_resume_version(version_id: int, db: Session = Depends(get_db)):
    version = db.query(ResumeVersion).filter(ResumeVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Resume version not found")
    db.delete(version)
    db.commit()
    return {"success": True}


@router.patch("/versions/{version_id}", response_model=ResumeVersionOut)
def update_resume_version_used_for(
    version_id: int,
    payload: ResumeVersionUpdateUsedFor,
    db: Session = Depends(get_db),
):
    version = db.query(ResumeVersion).filter(ResumeVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Resume version not found")

    version.used_for = payload.used_for
    db.commit()
    db.refresh(version)
    return version
