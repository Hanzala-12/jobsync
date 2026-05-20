import json
from typing import List, Optional
import re

from fastapi import APIRouter, Depends
from starlette.responses import StreamingResponse
import json
import threading
import concurrent.futures
import time as _time
import logging
import os
from backend import services as _services
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
from backend.services.job_apis import clean_text, get_pakistan_source_status, search_jobs
from core.deduplicator import process_incoming_job
from core.llm_provider import LLMProvider
from core.normalizer import normalize_job
# lazy import RAG functions inside _upsert_jobs to avoid heavy startup imports
from backend.database import engine

router = APIRouter(prefix="/jobs", tags=["Jobs"])
_logger = logging.getLogger(__name__)


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

        if resume_summary and saved_job and getattr(saved_job, "id", None) and cover_enabled:
            # Run cover letter generation asynchronously to avoid blocking search response.
            def _bg_generate(job_id, resume_text, company, role, job_description, source, job_url):
                try:
                    from backend.database import SessionLocal
                    from core.rag_service import generate_cover_letter_with_rag, save_cover_letter_artifacts

                    db_session = SessionLocal()
                    try:
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
                    finally:
                        try:
                            db_session.close()
                        except Exception:
                            pass
                except Exception as exc:
                    _logger.exception("Background cover letter generation failed: %s", exc)

            try:
                t = threading.Thread(
                    target=_bg_generate,
                    args=(saved_job.id, resume_summary, saved_job.company or raw_job["company"], saved_job.title or raw_job["title"], saved_job.description or raw_job["description"], saved_job.source, saved_job.url),
                )
                t.daemon = True
                t.start()
            except Exception:
                _logger.exception("Failed to start cover letter background thread")
                _logger.warning("Cover letter generation enabled but background threading unavailable; generation may block search responses.")

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
    # First check prefetched jobs cache for fast responses
    try:
        words = [w for w in re.findall(r"[a-z0-9+#.]+", (query or "").lower()) if len(w) > 2]
        if words:
            where_clauses = []
            params = []
            for w in words:
                clause = "(lower(title) LIKE ? OR lower(description) LIKE ?)"
                where_clauses.append(clause)
                like = f"%{w}%"
                params.extend([like, like])
            sql = "SELECT job_id, title, company, description, source FROM prefetched_jobs WHERE " + " AND ".join(where_clauses) + " ORDER BY fetched_at DESC LIMIT 50"
            with engine.connect() as conn:
                rows = conn.execute(sql, params).fetchall()
                if rows and len(rows) >= 5:
                    jobs = []
                    for r in rows:
                        jobs.append({
                            "external_id": r[0],
                            "title": r[1],
                            "company": r[2],
                            "description": r[3],
                            "source": r[4],
                            "url": r[0] if (r[0] and r[0].startswith("http")) else "",
                        })
                    for job in jobs:
                        job["description"] = clean_text(job.get("description", ""))
                    return _upsert_jobs(db, jobs)
    except Exception:
        # on any error, fall back to live search
        pass

    # Not enough prefetched results; perform live search and update cache asynchronously
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

    # Update cache in background (fire-and-forget)
    try:
        def _bg_update_cache(jobs_list):
            try:
                from backend.job_indexer import _upsert_prefetched
                for j in jobs_list:
                    try:
                        _upsert_prefetched(j)
                    except Exception:
                        pass
            except Exception:
                pass

        t = threading.Thread(target=_bg_update_cache, args=(jobs,))
        t.daemon = True
        t.start()
    except Exception:
        pass

    return _upsert_jobs(db, jobs)


@router.get('/search/stream')
def search_jobs_stream(
    query: str = 'software engineer',
    location: str = 'Pakistan',
    city: Optional[str] = None,
    remote_only: bool = False,
    pakistan_only: bool = False,
    country_code: str = 'pk',
):
    """Stream job search results as server-sent events (SSE) for progressive rendering."""

    def event_stream():
        start_ts = _time.time()
        combined = []
        seen_keys = set()

        # build list of source callables depending on location
        src_calls = []
        # fast sources
        src_calls.append(lambda: _services.job_apis.fetch_rozee_pakistan(query, city or location, max_pages=1))
        src_calls.append(lambda: _services.job_apis.fetch_mustakbil_pakistan(query, city or location, max_pages=1))
        src_calls.append(lambda: _services.job_apis.fetch_bing_pakistan(query, city or location, max_pages=1))
        src_calls.append(lambda: _services.job_apis.fetch_brightspyre(query, max_pages=1))
        src_calls.append(lambda: _services.job_apis.fetch_linkedin_indexed(query, city or location, max_jobs=4))
        src_calls.append(lambda: _services.job_apis.fetch_company_careers(query, company_limit=6))

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(src_calls)) as executor:
            future_to_name = {executor.submit(call): f"source_{index}" for index, call in enumerate(src_calls)}
            pending = set(future_to_name)

            while pending:
                done, pending = concurrent.futures.wait(
                    pending,
                    timeout=0.5,
                    return_when=concurrent.futures.FIRST_COMPLETED,
                )
                if not done:
                    continue

                for fut in done:
                    name = future_to_name.get(fut, "unknown")
                    try:
                        res = fut.result(timeout=0)
                    except Exception as exc:
                        _logger.warning("stream source failed: %s (%s)", name, exc)
                        res = []

                    new = []
                    for job in res:
                        key = job.get('external_id') or f"{job.get('title')}::{job.get('company')}::{job.get('url')}"
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        new.append(job)
                        combined.append(job)

                    payload = {
                        'partial': new,
                        'combined_count': len(combined),
                        'elapsed': round(_time.time() - start_ts, 2),
                    }
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            if len(combined) < 5:
                try:
                    indexed = _services.job_apis.fetch_indexed_pakistan(query, city or location, max_urls=6)
                    new = []
                    for job in indexed:
                        key = job.get('external_id') or f"{job.get('title')}::{job.get('company')}::{job.get('url')}"
                        if key in seen_keys:
                            continue
                        seen_keys.add(key)
                        new.append(job)
                        combined.append(job)
                    if new:
                        payload = {'partial': new, 'combined_count': len(combined), 'elapsed': round(_time.time() - start_ts, 2)}
                        yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                except Exception as exc:
                    _logger.warning("indexed fallback failed: %s", exc)

        # Final event with done flag and all combined results
        final = {'done': True, 'results': combined, 'elapsed': round(_time.time() - start_ts, 2)}
        yield f"data: {json.dumps(final, ensure_ascii=False)}\n\n"

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


@router.get("/autocomplete")
def autocomplete_keywords(query: str = "", db: Session = Depends(get_db)):
    """Return matching job keywords for autocomplete dropdown from config + stored jobs."""
    from config.pakistan_jobs_config import KEYWORDS
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
