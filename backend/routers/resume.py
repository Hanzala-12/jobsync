from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import UserProfile
from backend.services.pdf_parser import extract_text_from_pdf
from core.llm_provider import LLMProvider
from backend.schemas import ResumeAnalysis, ResumeReanalysisRequest
import tempfile
import json

router = APIRouter(prefix="/resume", tags=["Resume"])

@router.post("/analyze", response_model=ResumeAnalysis)
async def analyze_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    text = extract_text_from_pdf(tmp_path)

    # AI analysis
    prompt = f"""Analyze this resume text for a tech job. Give:
1. ATS score (0-100)
2. Matched skills (list)
2. Missing important keywords (list)
3. Three specific improvement tips
Resume: {text[:3000]}
Respond in JSON format: {{"score": number, "matched_skills": ["..."], "keywords": ["..."], "tips": ["..."]}}"""

    llm = LLMProvider()
    response = llm.ask("You are a helpful career AI assistant.", prompt)
    import json
    try:
        resp_json = json.loads(response)
        score = float(resp_json.get("score", 50.0))
        matched_skills = resp_json.get("matched_skills", resp_json.get("keywords", []))
        keywords = resp_json.get("keywords", [])
        tips = resp_json.get("tips", [])
    except Exception:
        # fallback
        score = 50.0
        matched_skills = []
        keywords = ["Could not parse"]
        tips = ["Add more keywords"]

    # Save / update user profile
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
    """Re-analyze the stored resume against a different job description."""
    profile = db.query(UserProfile).first()
    if not profile or not profile.resume_text:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    resume_text = profile.resume_text
    prompt = f"""Compare this resume to the job description and return JSON only.

Resume:
{resume_text[:3000]}

Job Description:
{req.job_description[:3000]}

Return exactly this JSON schema:
{{
  "score": number,
  "matched_skills": ["skill1", "skill2"],
  "missing_keywords": ["skill3", "skill4"],
  "tips": ["tip1", "tip2", "tip3"]
}}

Do not include markdown, commentary, or extra text.
"""

    llm = LLMProvider()
    response = llm.ask("You are a strict ATS resume analyzer.", prompt)

    try:
        resp_json = json.loads(response)
        score = float(resp_json.get("score", 50.0))
        matched_skills = resp_json.get("matched_skills", [])
        missing_keywords = resp_json.get("missing_keywords", [])
        tips = resp_json.get("tips", [])
    except Exception:
        score = 50.0
        matched_skills = []
        missing_keywords = ["Could not parse"]
        tips = ["Try re-running the analysis against the job description."]

    profile.latest_ats_score = score
    profile.skills = ", ".join(matched_skills) if matched_skills else profile.skills
    db.commit()

    return ResumeAnalysis(
        ats_score=score,
        matched_skills=matched_skills,
        missing_keywords=missing_keywords,
        tips=tips,
        resume_text=resume_text,
    )
