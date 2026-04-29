"""
Voice Interview Mock - AI-powered interview practice
"""
from fastapi import APIRouter
from pydantic import BaseModel
from core.llm_provider import LLMProvider

router = APIRouter(prefix="/interview", tags=["Interview"])

class AnswerEval(BaseModel):
    question: str
    answer: str  # transcribed from voice or typed

@router.post("/evaluate")
def evaluate_answer(req: AnswerEval):
    """Evaluate interview answer and provide feedback"""
    llm = LLMProvider()
    
    prompt = f"""As an interview coach, evaluate this answer to the question: "{req.question}"

Answer: "{req.answer}"

Provide:
1. Score out of 10
2. Strengths of the answer
3. Weaknesses and areas for improvement
4. A better sample answer

Be constructive and specific."""
    
    feedback = llm.ask("You are a strict but helpful interview coach.", prompt)
    
    return {
        "question": req.question,
        "your_answer": req.answer,
        "feedback": feedback
    }

@router.post("/generate-questions")
def generate_questions(job_title: str, company: str = ""):
    """Generate mock interview questions for a role"""
    llm = LLMProvider()
    
    prompt = f"""Generate 5 common interview questions for a {job_title} position{' at ' + company if company else ''}.

Include:
- 2 technical questions
- 2 behavioral questions
- 1 situational question

Format as a numbered list."""
    
    questions = llm.ask("You are an interview preparation expert.", prompt)
    
    return {
        "job_title": job_title,
        "company": company,
        "questions": questions
    }
