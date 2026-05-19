"""Interview APIs: question generation, answer evaluation, and personalized predictor."""

import json

from fastapi import APIRouter
from pydantic import BaseModel

from backend.schemas import InterviewPredictedQuestion, InterviewPredictRequest
from core.llm_provider import LLMProvider

router = APIRouter(prefix="/interview", tags=["Interview"])


class AnswerEval(BaseModel):
    question: str
    answer: str


class GenerateQuestionsInput(BaseModel):
    job_title: str
    company: str = ""


def _extract_json_array(response: str):
    if not response:
        return []

    raw = response.strip()
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except Exception:
        pass

    if "```" in raw:
        for part in raw.split("```"):
            cleaned = part.replace("json", "", 1).strip()
            if not cleaned:
                continue
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                continue

    start = raw.find("[")
    end = raw.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            parsed = json.loads(raw[start : end + 1])
            return parsed if isinstance(parsed, list) else []
        except Exception:
            pass

    return []


@router.post("/evaluate")
def evaluate_answer(req: AnswerEval):
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
        "feedback": feedback,
    }


@router.post("/generate-questions")
def generate_questions(payload: GenerateQuestionsInput):
    llm = LLMProvider()

    prompt = f"""Generate 5 common interview questions for a {payload.job_title} position{' at ' + payload.company if payload.company else ''}.

Include:
- 2 technical questions
- 2 behavioral questions
- 1 situational question

Format as a numbered list."""

    questions = llm.ask("You are an interview preparation expert.", prompt)

    return {
        "job_title": payload.job_title,
        "company": payload.company,
        "questions": questions,
    }


@router.post("/predict", response_model=list[InterviewPredictedQuestion])
def predict_interview_questions(payload: InterviewPredictRequest):
    llm = LLMProvider()
    prompt = f"""You are an interviewer at {payload.company} hiring for {payload.role}.
Generate questions this specific candidate will be asked.
Based on their resume and your job requirements generate:
- 4 technical questions (based on their stack)
- 3 behavioral questions (their experience level)
- 2 gap questions (things missing from resume)
- 1 curveball question
For each question include:
  question, why_asked, strong_answer_includes: [],
  difficulty: easy|medium|hard, type: technical|behavioral|gap|curveball
Job: {payload.job_description}
Resume: {payload.resume_text}
Return JSON array only."""

    parsed = _extract_json_array(
        llm.ask("You are a hiring manager creating role-specific interview questions.", prompt)
    )

    if not parsed:
        parsed = [
            {
                "question": "Describe a recent project where your work had measurable impact.",
                "why_asked": "To evaluate communication and ownership.",
                "strong_answer_includes": ["context", "actions", "metrics"],
                "difficulty": "easy",
                "type": "behavioral",
            }
        ]

    questions: list[InterviewPredictedQuestion] = []
    for item in parsed:
        try:
            questions.append(
                InterviewPredictedQuestion(
                    question=str(item.get("question", "")),
                    why_asked=str(item.get("why_asked", "")),
                    strong_answer_includes=[str(x) for x in (item.get("strong_answer_includes") or [])],
                    difficulty=str(item.get("difficulty", "medium")).lower(),
                    type=str(item.get("type", "technical")).lower(),
                )
            )
        except Exception:
            continue

    return questions
