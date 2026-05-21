import json
from typing import List, Optional, Dict
import re

from concurrent.futures import ThreadPoolExecutor
from fastapi import APIRouter, Depends, HTTPException
from starlette.responses import StreamingResponse
import json
import concurrent.futures
import time as _time
import logging
import os
from backend import services as _services
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.database import get_db
from backend.models import Job, UserProfile
from backend.schemas import (
    ExplainMatchRequest,
    JobMatch,
    JobMatchExplainResponse,
    JobOut,
    JobUpsert,
    SalaryEstimateRequest,
    SalaryEstimateResponse,
)
from backend.services.job_apis import clean_text, get_pakistan_source_status, search_jobs
import requests
from scrapers.rozee_scraper import ROZEE_USER_AGENT, BASE_URL
from core.deduplicator import process_incoming_job
from core.llm_provider import LLMProvider
from core.normalizer import normalize_job
# lazy import RAG functions inside _upsert_jobs to avoid heavy startup imports
from backend.database import engine

router = APIRouter(prefix="/jobs", tags=["Jobs"])
_logger = logging.getLogger(__name__)
_MAX_BG_WORKERS = max(1, int(os.getenv("MAX_BG_WORKERS", "5")))
_BG_EXECUTOR = ThreadPoolExecutor(max_workers=_MAX_BG_WORKERS, thread_name_prefix="jobsync-bg")


def _resolve_job_url(job: dict) -> str:
    primary = str(job.get("url") or "").strip()
    apply_url = str(job.get("apply_url") or "").strip()
    external_id = str(job.get("external_id") or "").strip()

    for candidate in (primary, apply_url, external_id):
        if candidate.startswith("http://") or candidate.startswith("https://"):
            return candidate
    return ""


def _normalize_stream_job(job: dict) -> dict:
    normalized = dict(job or {})
    resolved_url = _resolve_job_url(normalized)
    if resolved_url:
        normalized["url"] = resolved_url
        normalized["apply_url"] = str(normalized.get("apply_url") or resolved_url)
    return normalized


def shutdown_background_executor():
    try:
        _BG_EXECUTOR.shutdown(wait=False, cancel_futures=True)
    except Exception:
        _logger.exception("Failed to shut down background executor")


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
    profile = db.query(UserProfile).first()
    resume_summary = profile.resume_text[:1500] if profile and profile.resume_text else ""

    cover_enabled = os.getenv("ENABLE_JOB_ARTIFACTS", "false").lower() in {"1", "true", "yes"}
    if cover_enabled:
        _logger.warning("Cover letter generation enabled – search may be slower.")

    for job in jobs:
        resolved_url = _resolve_job_url(job)
        raw_job = {
            "title": clean_text(str(job.get("title") or "")),
            "company": clean_text(str(job.get("company") or "")),
            "city": job.get("city") or job.get("location") or "",
            "location": job.get("location") or job.get("city") or "",
            "description": clean_text(str(job.get("description") or "")),
            "apply_url": job.get("apply_url") or job.get("url") or resolved_url,
            "url": job.get("url") or job.get("apply_url") or resolved_url,
            "posted_date": job.get("posted_date") or "",
            "salary": job.get("salary") or "",
            "external_id": str(job.get("external_id") or job.get("url") or "").strip() or None,
        }
        normalized = normalize_job(raw_job, str(job.get("source") or "unknown"))
        saved_job, _ = process_incoming_job(db, normalized)
        saved_jobs.append(saved_job)

        if resume_summary and saved_job and getattr(saved_job, "id", None) and cover_enabled:
            try:
                future = _BG_EXECUTOR.submit(
                    _bg_generate_cover_letter,
                    saved_job.id,
                    resume_summary,
                    saved_job.company or raw_job["company"],
                    saved_job.title or raw_job["title"],
                    saved_job.description or raw_job["description"],
                    saved_job.source,
                    saved_job.url,
                )
                future.add_done_callback(_log_background_future_error)
            except Exception:
                _logger.exception("Failed to submit cover letter background task")
                _logger.warning("Cover letter generation enabled but background threading unavailable; generation may block search responses.")

    return saved_jobs


def _log_background_future_error(future):
    try:
        future.result()
    except Exception:
        _logger.exception("Background cover letter generation failed")


def _bg_generate_cover_letter(job_id, resume_text, company, role, job_description, source, job_url):
    from core.rag_service import generate_cover_letter_with_rag, save_cover_letter_artifacts

    draft, source_ids, retrieved_chunks = generate_cover_letter_with_rag(
        job_description,
        resume_text,
        company_name=company,
        role=role,
        tone="professional",
        top_k=5,
        metadata_filter={"company": company} if company else None,
    )
    save_cover_letter_artifacts(
        job_id,
        draft,
        source_ids,
        retrieved_chunks,
        metadata={
            "company": company,
            "role": role,
            "source": source,
            "job_url": job_url,
        },
    )


@router.get("/search", response_model=List[JobOut])
def search_jobs_endpoint(
    query: str = "software engineer",
    location: str = "Pakistan",
    city: Optional[str] = None,
    remote_only: bool = False,
    pakistan_only: bool = False,
    country_code: str = "pk",
    page: int = 1,
    limit: int = 20,
    sort: str = "newest",
    db: Session = Depends(get_db),
):
    # Database-only search: do not perform live scraping during user requests.

    # Build base query
    q = db.query(Job).filter(Job.is_active == True)
    if query:
        term = f"%{query.lower()}%"
        q = q.filter(
            (func.lower(Job.title).like(term)) | (func.lower(Job.description).like(term))
        )
    if city:
        q = q.filter(func.lower(Job.city) == city.strip().lower())

    if sort == "newest":
        q = q.order_by(Job.scraped_at.desc().nullslast(), Job.fetched_at.desc().nullslast())
    else:
        q = q.order_by(Job.fetched_at.desc().nullslast())

    total = q.count()
    page = max(1, page)
    limit = max(1, min(100, limit))
    items = q.offset((page - 1) * limit).limit(limit).all()

    def job_to_out(j: Job):
        return JobOut.model_validate(
            {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "location": j.location,
                "description": j.description,
                "url": j.url,
                "source": j.source,
                "posted_date": j.posted_date,
                "salary": j.salary,
            }
        )

    return [job_to_out(j) for j in items]


@router.get('/test_rozee')
def test_rozee_endpoint(query: str = 'software engineer', city: Optional[str] = None):
    """Diagnostic endpoint: backend fetches Rozee search page and returns status and link count."""
    city_slug = (city or 'pakistan').strip().lower().replace(' ', '-')
    query_slug = (query or 'software engineer').strip().lower().replace(' ', '-')
    url = f"{BASE_URL}/search/{query_slug}-jobs-in-{city_slug}"
    headers = {"User-Agent": ROZEE_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        text = resp.text or ''
        import re as _re
        link_count = len(_re.findall(r"-jobs-[0-9]+", text))
        snippet = text[:2000]
        return {"url": url, "status_code": resp.status_code, "link_count": link_count, "snippet": snippet}
    except Exception as exc:
        return {"url": url, "error": str(exc)}


@router.get("/search/diagnostics")
def search_jobs_diagnostics(
    query: str = "software engineer",
    location: str = "Pakistan",
    city: Optional[str] = None,
    remote_only: bool = False,
    pakistan_only: bool = False,
    country_code: str = "pk",
    db: Session = Depends(get_db),
):
    diagnostics: Dict = {}
    # Return diagnostics about DB query execution instead of live scraping
    try:
        q = db.query(Job).filter(Job.is_active == True)
        if query:
            term = f"%{query.lower()}%"
            q = q.filter((func.lower(Job.title).like(term)) | (func.lower(Job.description).like(term)))
        items = q.order_by(Job.scraped_at.desc().nullslast()).limit(50).all()
        job_dicts = [
            {
                "id": j.id,
                "external_id": j.external_id,
                "title": j.title,
                "company": j.company,
                "description": j.description,
                "source": j.source,
                "url": j.url,
                "apply_url": j.apply_url,
                "location": j.location,
                "salary": j.salary,
                "posted_date": j.posted_date,
            }
            for j in items
        ]
        diagnostics["source"] = "database"
    except Exception as exc:
        diagnostics["error"] = str(exc)
        job_dicts = []

    return {"jobs": job_dicts, "diagnostics": diagnostics}


@router.get('/search/stream')
def search_jobs_stream(
    query: str = 'software engineer',
    location: str = 'Pakistan',
    city: Optional[str] = None,
    remote_only: bool = False,
    pakistan_only: bool = False,
    country_code: str = 'pk',
    db: Session = Depends(get_db),
):
    def event_stream():
        q = db.query(Job).filter(Job.is_active == True)
        if query:
            term = f"%{query.lower()}%"
            q = q.filter((func.lower(Job.title).like(term)) | (func.lower(Job.description).like(term)))
        items = q.order_by(Job.scraped_at.desc().nullslast()).limit(100).all()
        for j in items:
            payload = {
                "id": j.id,
                "title": j.title,
                "company": j.company,
                "description": j.description,
                "source": j.source,
                "url": j.url,
            }
            yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
        yield f"event: done\ndata: {json.dumps({'total': len(items)})}\n\n"

    return StreamingResponse(event_stream(), media_type='text/event-stream')


@router.get("/sources")
def sources_status():
    return {"sources": get_pakistan_source_status()}


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
    # If no LLM provider is configured, use a simple local heuristic based on
    # keyword overlap so Match still works offline.
    if not getattr(llm, 'provider_type', None):
        import re as _re

        def _words(text: str):
            return set([w for w in _re.findall(r"[a-zA-Z0-9+#.+]+", (text or "").lower()) if len(w) > 2])

        profile = db.query(UserProfile).first()
        resume_text = profile.resume_text if profile and profile.resume_text else ""
        resume_words = _words(resume_text)
        job_words = _words(job.description or "")
        if not job_words:
            return JobMatch(job_id=job_id, match_percentage=0.0, explanation="No job description text to analyze", missing_skills=[])

        overlap = resume_words & job_words
        match_pct = int(min(100, (len(overlap) / max(1, len(job_words))) * 100))
        missing = sorted(list((job_words - resume_words)))[:12]
        explanation = f"Heuristic match based on keyword overlap: {len(overlap)} of {len(job_words)} job keywords found in resume."
        return JobMatch(job_id=job_id, match_percentage=float(match_pct), explanation=explanation, missing_skills=missing)

    raw = llm.ask("You are a hiring expert.", prompt)
    # If the provider returned an explicit error string, propagate it as a 503
    if isinstance(raw, str) and raw.startswith("AI error:"):
        raise HTTPException(status_code=503, detail=raw.replace("AI error:", "").strip() or "AI provider unavailable")

    data = _extract_json(
        raw,
        {"percentage": 0, "explanation": "Failed to parse AI response", "missing_skills": []},
    )

    return JobMatch(
        job_id=job_id,
        match_percentage=float(data.get("percentage", 0)),
        explanation=str(data.get("explanation", "")),
        missing_skills=[str(skill) for skill in (data.get("missing_skills") or [])],
    )


@router.post("/upsert", response_model=JobOut)
def upsert_job(payload: JobUpsert, db: Session = Depends(get_db)):
    """Create or update a job in the local DB and return the stored job object.

    Accepts a dict with keys similar to the job objects returned by scrapers
    (title, company, description, url, source, external_id, location, city, etc.).
    """
    try:
        raw_job = {
            "title": clean_text(str(payload.title or "")),
            "company": clean_text(str(payload.company or "")),
            "city": payload.city or payload.location or "",
            "location": payload.location or payload.city or "",
            "description": clean_text(str(payload.description or "")),
            "apply_url": payload.apply_url or payload.url or "",
            "url": payload.url or payload.apply_url or "",
            "posted_date": payload.posted_date or "",
            "salary": payload.salary or "",
            "external_id": str(payload.external_id or payload.url or "").strip() or None,
            "source": payload.source or "unknown",
        }

        normalized = normalize_job(raw_job, str(raw_job.get("source") or "unknown"))
        saved_job, _ = process_incoming_job(db, normalized)
        if not saved_job:
            raise HTTPException(status_code=500, detail="Failed to upsert job")

        return saved_job
    except HTTPException:
        raise
    except Exception as exc:
        _logger.exception("Upsert job failed: %s", exc)
        raise HTTPException(status_code=500, detail="Upsert failed")


@router.post("/explain-match", response_model=JobMatchExplainResponse)
def explain_match(payload: ExplainMatchRequest):
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


@router.get("/autocomplete")
def autocomplete_keywords(query: str = "", db: Session = Depends(get_db)):
    """Return matching job keywords for autocomplete dropdown from config + stored jobs."""
    from backend.config.pakistan_jobs_config import KEYWORDS
    from backend.models import Job
    
    if not query or len(query) < 1:
        return {"suggestions": []}
    
    query_lower = query.lower().strip()
    matches = set()
    
    # 1. Filter config keywords
    for keyword in KEYWORDS:
        keyword_lower = keyword.lower()
        if keyword_lower.startswith(query_lower) or query_lower in keyword_lower:
            matches.add(keyword)
    
    # 2. Add job titles from database that match query
    try:
        db_jobs = db.query(Job.title).filter(
            Job.title.ilike(f"%{query_lower}%")
        ).distinct().limit(20).all()
        for (title,) in db_jobs:
            if title and len(title) < 100:  # Avoid overly long titles
                matches.add(title)
    except Exception:
        pass
    
    # Sort by relevance (exact prefix matches first)
    sorted_matches = sorted(matches, key=lambda k: (not k.lower().startswith(query_lower), k))
    
    # Return top 15 matches (more now that we include DB jobs)
    return {"suggestions": sorted_matches[:15]}
