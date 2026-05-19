import json
from typing import List, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Job, UserProfile
from backend.schemas import (
    JobMatch,
    JobMatchExplainRequest,
    JobMatchExplainResponse,
    JobOut,
    SalaryEstimateRequest,
    SalaryEstimateResponse,
)
from backend.services.job_apis import clean_text, search_jobs
from core.deduplicator import process_incoming_job
from core.llm_provider import LLMProvider
from core.normalizer import normalize_job

router = APIRouter(prefix="/jobs", tags=["Jobs"])


def _extract_json(response: str, fallback):
    if not response:
        return fallback

    raw = response.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass

    if "```" in raw:
        for part in raw.split("```"):
            cleaned = part.replace("json", "", 1).strip()
            if not cleaned:
                continue
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


def _upsert_jobs(db: Session, jobs: List[dict]) -> List[Job]:
    saved_jobs: List[Job] = []

    for job in jobs:
        raw_job = {
            "title": clean_text(str(job.get("title") or "")),
            "company": clean_text(str(job.get("company") or "")),
            "city": job.get("city") or job.get("location") or "",
            "location": job.get("location") or job.get("city") or "",
            "description": clean_text(str(job.get("description") or "")),
            "apply_url": job.get("apply_url") or job.get("url") or "",
            "url": job.get("url") or job.get("apply_url") or "",
            "posted_date": job.get("posted_date") or "",
            "salary": job.get("salary") or "",
            "external_id": str(job.get("external_id") or job.get("url") or "").strip() or None,
        }
        normalized = normalize_job(raw_job, str(job.get("source") or "unknown"))
        saved_job, _ = process_incoming_job(db, normalized)
        saved_jobs.append(saved_job)

    return saved_jobs


@router.get("/search", response_model=List[JobOut])
def search_jobs_endpoint(
    query: str = "software engineer",
    location: str = "Pakistan",
    city: Optional[str] = None,
    remote_only: bool = False,
    pakistan_only: bool = False,
    country_code: str = "pk",
    db: Session = Depends(get_db),
):
    jobs = search_jobs(
        query=query,
        location=location,
        city=city,
        remote_only=remote_only,
        pakistan_only=pakistan_only,
        country_code=country_code,
    )

    for job in jobs:
        job["description"] = clean_text(job.get("description", ""))

    return _upsert_jobs(db, jobs)


@router.get("/{job_id}/match", response_model=JobMatch)
def match_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JobMatch(job_id=job_id, match_percentage=0, explanation="Job not found", missing_skills=[])

    profile = db.query(UserProfile).first()
    if not profile or not profile.resume_text:
        return JobMatch(job_id=job_id, match_percentage=0, explanation="Upload resume first", missing_skills=[])

    prompt = f"""Compare the resume with the job description.
Resume: {profile.resume_text[:2000]}
Job Description: {job.description[:2000]}
Give:
- Match percentage (0-100)
- Explanation (why this score)
- List missing skills
Respond as JSON: {{"percentage": number, "explanation": "string", "missing_skills": ["..."]}}"""

    llm = LLMProvider()
    data = _extract_json(
        llm.ask("You are a hiring expert.", prompt),
        {"percentage": 0, "explanation": "Failed to parse AI response", "missing_skills": []},
    )

    return JobMatch(
        job_id=job_id,
        match_percentage=float(data.get("percentage", 0)),
        explanation=str(data.get("explanation", "")),
        missing_skills=[str(skill) for skill in (data.get("missing_skills") or [])],
    )


@router.post("/explain-match", response_model=JobMatchExplainResponse)
def explain_match(payload: JobMatchExplainRequest):
    llm = LLMProvider()
    prompt = f"""Analyze this resume against this job description.
Write 3 paragraphs in plain English:
1: Strong fit reasons (name actual skills)
2: Missing or weak areas (be honest)
3: One specific thing to do this week
Return JSON only:
{{"paragraph1": "...", "paragraph2": "...", "paragraph3": "...", "match_score": 0, "matched_skills": [], "missing_skills": [], "quick_win": "..."}}
Resume: {payload.resume_text}
Job Description: {payload.job_description}"""

    data = _extract_json(
        llm.ask("You are a practical career coach.", prompt),
        {
            "paragraph1": "Your resume has some overlap with the role requirements.",
            "paragraph2": "Some required keywords and experiences are not explicit yet.",
            "paragraph3": "Update two bullet points this week to reflect measurable impact.",
            "match_score": 55,
            "matched_skills": [],
            "missing_skills": [],
            "quick_win": "Tailor your project bullets to this job's core requirements.",
        },
    )

    return JobMatchExplainResponse(
        paragraph1=str(data.get("paragraph1", "")),
        paragraph2=str(data.get("paragraph2", "")),
        paragraph3=str(data.get("paragraph3", "")),
        match_score=int(max(0, min(100, int(data.get("match_score", 0))))),
        matched_skills=[str(skill) for skill in (data.get("matched_skills") or [])],
        missing_skills=[str(skill) for skill in (data.get("missing_skills") or [])],
        quick_win=str(data.get("quick_win", "")),
    )


@router.post("/salary-estimate", response_model=SalaryEstimateResponse)
def salary_estimate(payload: SalaryEstimateRequest):
    llm = LLMProvider()
    prompt = f"""Estimate salary for this position in Pakistan market.
Be realistic. Include remote/international comparison.
Title: {payload.title}, Location: {payload.location}
Experience: {payload.experience_level}, Skills: {payload.skills}
Return JSON only:
{{"local_min": 0, "local_max": 0, "remote_min": 0, "remote_max": 0, "market_demand": "high|medium|low", "negotiation_tip": "...", "top_paying_companies": ["A", "B", "C"]}}"""

    data = _extract_json(
        llm.ask("You are a compensation analyst for Pakistan's tech market.", prompt),
        {
            "local_min": 120000,
            "local_max": 250000,
            "remote_min": 1500,
            "remote_max": 4500,
            "market_demand": "medium",
            "negotiation_tip": "Present quantified impact from recent work when discussing compensation.",
            "top_paying_companies": ["Systems Limited", "Careem", "10Pearls"],
        },
    )

    return SalaryEstimateResponse(
        local_min=int(data.get("local_min", 0)),
        local_max=int(data.get("local_max", 0)),
        remote_min=int(data.get("remote_min", 0)),
        remote_max=int(data.get("remote_max", 0)),
        market_demand=str(data.get("market_demand", "medium")).lower(),
        negotiation_tip=str(data.get("negotiation_tip", "")),
        top_paying_companies=[str(item) for item in (data.get("top_paying_companies") or [])][:3],
    )
