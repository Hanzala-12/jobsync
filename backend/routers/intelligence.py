from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.schemas import SkillGapRequest, SkillGapResponse, InterviewPrepRequest, InterviewPrepResponse, InterviewQuestion
from backend.services.ai_client import ask_llm
from backend.models import UserProfile
import json

router = APIRouter(prefix="/intelligence", tags=["Intelligence"])

@router.post("/skill-gap", response_model=SkillGapResponse)
def skill_gap_analysis(req: SkillGapRequest, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).first()
    my_skills = profile.skills if profile else ""

    descs = "\n".join([f"- {d[:500]}" for d in req.job_descriptions[:10]])
    prompt = f"""Given these job descriptions:
{descs}
And my current skills: {my_skills}
List the top 5 skills that appear frequently in the jobs but are missing from my list.
Return JSON: {{"missing_skills": ["skill1", "skill2"], "frequency": {{"skill1": count, ...}}}}"""

    response = ask_llm(prompt)
    try:
        data = json.loads(response)
        return SkillGapResponse(**data)
    except:
        return SkillGapResponse(missing_skills=["parsing error"], frequency={})

@router.post("/interview-prep", response_model=InterviewPrepResponse)
def interview_prep(req: InterviewPrepRequest, db: Session = Depends(get_db)):
    prompt = f"""Generate 10 likely interview questions for the role '{req.role}'.
Job description context: {req.job_description or 'Not provided'}
Return JSON: {{"questions": [{{"question": "...", "suggested_answer": "..."}}]}}"""

    response = ask_llm(prompt)
    try:
        data = json.loads(response)
        questions = [InterviewQuestion(**q) for q in data["questions"]]
        return InterviewPrepResponse(questions=questions)
    except:
        # fallback
        return InterviewPrepResponse(questions=[InterviewQuestion(question="AI error – try again.", suggested_answer="")])
