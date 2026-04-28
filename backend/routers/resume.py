from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.models import UserProfile
from backend.services.pdf_parser import extract_text_from_pdf
from backend.services.ai_client import ask_llm
from backend.schemas import ResumeAnalysis
import tempfile

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
2. Missing important keywords (list)
3. Three specific improvement tips
Resume: {text[:3000]}
Respond in JSON format: {{"score": number, "keywords": ["...",], "tips": ["..."]}}"""

    response = ask_llm(prompt)
    import json
    try:
        # Simple parse - in production use structured output
        resp_json = json.loads(response)
        score = float(resp_json["score"])
        keywords = resp_json["keywords"]
        tips = resp_json["tips"]
    except:
        # fallback
        score = 50.0
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

    return ResumeAnalysis(ats_score=score, missing_keywords=keywords, tips=tips)
