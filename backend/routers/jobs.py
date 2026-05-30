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
from sqlalchemy import func, or_

from backend.database import get_db
from backend.models import Job, UserProfile
from backend.services.job_interactions import record_user_job_interaction
from backend.schemas import (
    ExplainMatchRequest,
    JobMatch,
    JobMatchExplainResponse,
    JobOut,
    JobUpsert,
    SalaryEstimateRequest,
    SalaryEstimateResponse,
)
from backend.services.job_apis import (
    clean_text,
    fetch_bing_pakistan,
    fetch_brightspyre,
    fetch_company_careers,
    fetch_linkedin_indexed,
    fetch_mustakbil_pakistan,
    fetch_rozee_pakistan,
    get_pakistan_source_status,
        search_jobs,
        _query_variants,
)
from backend.services.job_ranking import rerank_job_candidates
import requests
from scrapers.rozee_scraper import ROZEE_USER_AGENT, BASE_URL
from core.deduplicator import process_incoming_job
from core.llm_provider import LLMProvider
from core.normalizer import normalize_job
from core.skill_extractor import extract_skills
from core.match_explainer import explain_match_for
from backend.services.profile_data import parse_int, parse_string_list, parse_float
# lazy import RAG functions inside _upsert_jobs to avoid heavy startup imports
from backend.database import engine
from backend.security import get_current_user, get_current_user_from_stream, get_optional_current_user
from backend.tasks.cover_letter_tasks import dispatch_cover_letter_generation

router = APIRouter(prefix="/jobs", tags=["Jobs"])
_logger = logging.getLogger(__name__)
_MAX_BG_WORKERS = max(1, int(os.getenv("MAX_BG_WORKERS", "5")))
_BG_EXECUTOR = ThreadPoolExecutor(max_workers=_MAX_BG_WORKERS, thread_name_prefix="jobsync-bg")
ENABLE_LIVE_SEARCH_FALLBACK = os.getenv("ENABLE_LIVE_SEARCH_FALLBACK", "true").strip().lower() in {"1", "true", "yes", "on"}
MOCK_COMPANY_NAMES = {
    "brand demand",
    "test company",
    "testco",
    "seedai labs",
    "vectorai",
    "deepsignal",
}


def _real_job_query(query):
    return query.filter(
        Job.source.isnot(None),
        func.lower(Job.source) != "seed",
        func.lower(Job.url).notlike("%example.com%"),
        func.lower(Job.apply_url).notlike("%example.com%"),
        func.lower(func.coalesce(Job.company, "")).notin_(MOCK_COMPANY_NAMES),
    )


def _is_mock_company(value: Optional[str]) -> bool:
    return clean_text(value).strip().lower() in MOCK_COMPANY_NAMES


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


def _normalize_skill_list(values) -> List[str]:
    if values is None:
        return []

    if isinstance(values, str):
        raw_values = re.split(r"[\n,;|•]+", values)
    elif isinstance(values, (list, tuple, set)):
        raw_values = list(values)
    else:
        raw_values = [values]

    cleaned: List[str] = []
    seen = set()
    for item in raw_values:
        skill = re.sub(r"\s+", " ", str(item or "")).strip(" -:\t\r\n")
        if len(skill) <= 1:
            continue
        lowered = skill.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(skill)
    return cleaned


def _parse_salary_value(value: str | None) -> int | None:
    if not value:
        return None
    text = str(value).lower().replace(",", "")
    match = re.search(r"(?:pk)?r?\$?\s*(\d+(?:\.\d+)?)\s*([km]?)", text)
    if not match:
        match = re.search(r"(\d+(?:\.\d+)?)", text)
        if not match:
            return None
        return int(float(match.group(1)))
    amount = float(match.group(1))
    suffix = match.group(2)
    if suffix == "k":
        amount *= 1000
    elif suffix == "m":
        amount *= 1000000
    return int(amount)


def _profile_skill_values(profile: UserProfile | None) -> list[str]:
    if not profile:
        return []
    values = getattr(profile, "skills", None)
    if values:
        return parse_string_list(values)
    resume_text = getattr(profile, "resume_text", None) or ""
    return extract_skills(resume_text, limit=50)


def _get_selected_profile(db: Session, user_id: int) -> UserProfile | None:
    try:
        from backend.models import UserPreference

        selected_id = None
        pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).order_by(UserPreference.updated_at.desc(), UserPreference.id.desc()).first()
        if pref and pref.selected_profile_id:
            selected_id = int(pref.selected_profile_id)
        if selected_id:
            profile = db.query(UserProfile).filter(UserProfile.id == selected_id, UserProfile.user_id == user_id).first()
            if profile:
                return profile
    except Exception:
        pass
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).order_by(UserProfile.created_at.desc(), UserProfile.id.desc()).first()


def _score_job_for_profile(job: Job, profile: UserProfile | None) -> tuple[float, bool]:
    if not profile:
        return 0.0, True

    title = (job.title or "").lower()
    description = (job.description or "").lower()
    location_text = " ".join(filter(None, [job.location, job.city])).lower()

    preferred_titles = [item.lower() for item in parse_string_list(getattr(profile, "preferred_job_titles", None))]
    profile_location = (profile.location or "").lower()
    preferred_work_location = (profile.preferred_work_location or "").lower()
    profile_skills = [skill.lower() for skill in _profile_skill_values(profile)]
    job_skills = [skill.lower() for skill in parse_string_list(getattr(job, "job_skills", None))]

    score = 0.0
    if preferred_titles:
        if any(title_pref in title for title_pref in preferred_titles):
            score += 28
        if any(title_pref in description for title_pref in preferred_titles):
            score += 14

    if profile_skills:
        overlap = {skill for skill in profile_skills if skill and (skill in title or skill in description or skill in job_skills)}
        score += min(30, len(overlap) * 5)

    if profile_location and profile_location in location_text:
        score += 12
    elif profile_location and any(part in location_text for part in profile_location.split() if len(part) > 2):
        score += 6

    if preferred_work_location:
        if preferred_work_location in {"remote", "hybrid", "onsite"}:
            if preferred_work_location == "remote" and ("remote" in title or "remote" in description or "remote" in location_text):
                score += 10
            elif preferred_work_location == "hybrid" and "hybrid" in (title + " " + description + " " + location_text):
                score += 8
            elif preferred_work_location == "onsite" and "onsite" in (title + " " + description + " " + location_text):
                score += 8
        elif preferred_work_location in location_text:
            score += 8

    salary_min = parse_int(getattr(profile, "desired_salary_min", None))
    salary_max = parse_int(getattr(profile, "desired_salary_max", None))
    parsed_salary = _parse_salary_value(job.salary)
    if salary_min and parsed_salary and parsed_salary < salary_min:
        return score - 50, False
    if salary_max and parsed_salary and parsed_salary > salary_max:
        score -= 6

    if getattr(profile, "willing_to_relocate", False) and location_text:
        score += 2

    return score, True


def _extract_skills_from_text(text: str, limit: int = 12) -> List[str]:
    source = (text or "").lower()
    skill_patterns = [
        ("Python", r"\bpython\b"),
        ("JavaScript", r"\bjavascript\b|\bjs\b"),
        ("TypeScript", r"\btypescript\b|\bts\b"),
        ("React", r"\breact\b"),
        ("Node.js", r"\bnode(?:\.js)?\b"),
        ("Django", r"\bdjango\b"),
        ("Flask", r"\bflask\b"),
        ("FastAPI", r"\bfastapi\b"),
        ("REST APIs", r"\brest\s+api(?:s)?\b|\bapi(?:s)?\b"),
        ("SQL", r"\bsql\b"),
        ("PostgreSQL", r"\bpostgres(?:ql)?\b"),
        ("MySQL", r"\bmysql\b"),
        ("MongoDB", r"\bmongodb\b"),
        ("HTML", r"\bhtml\b"),
        ("CSS", r"\bcss\b"),
        ("Tailwind CSS", r"\btailwind(?: css)?\b"),
        ("Git", r"\bgit\b"),
        ("Docker", r"\bdocker\b"),
        ("Kubernetes", r"\bkubernetes\b|\bk8s\b"),
        ("AWS", r"\baws\b|amazon web services"),
        ("Azure", r"\bazure\b"),
        ("Machine Learning", r"\bmachine learning\b"),
        ("Deep Learning", r"\bdeep learning\b"),
        ("Data Analysis", r"\bdata analysis\b"),
        ("Data Science", r"\bdata science\b"),
        ("Pandas", r"\bpandas\b"),
        ("NumPy", r"\bnumpy\b"),
        ("Testing", r"\btesting\b|\btest automation\b|\bqa\b|\bselenium\b|\bpytest\b"),
        ("Communication", r"\bcommunication\b"),
        ("Teamwork", r"\bteamwork\b|\bcollaboration\b"),
        ("Problem Solving", r"\bproblem solving\b|\bproblem-solving\b"),
        ("Agile", r"\bagile\b|\bscrum\b"),
    ]

    extracted: List[str] = []
    for label, pattern in skill_patterns:
        if re.search(pattern, source):
            extracted.append(label)

    if not extracted:
        fallback_tokens = []
        token_counts: Dict[str, int] = {}
        for token in re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{2,}", source):
            if token in {"and", "for", "the", "with", "that", "this", "from", "your", "you", "are", "have", "will", "our", "their", "job", "role", "skills", "skill", "experience", "team", "work", "strong", "good", "knowledge", "ability", "required", "requirements"}:
                continue
            token_counts[token] = token_counts.get(token, 0) + 1
        ranked = sorted(token_counts.items(), key=lambda item: (-item[1], item[0]))
        fallback_tokens = [token for token, _ in ranked[:limit]]
        extracted = [token.replace(".", " ").strip().title() for token in fallback_tokens if token.strip()]

    cleaned: List[str] = []
    seen = set()
    for skill in extracted:
        lowered = skill.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(skill)
        if len(cleaned) >= limit:
            break
    return cleaned


def _upsert_jobs(db: Session, jobs: List[dict]) -> List[Job]:
    saved_jobs: List[Job] = []
    resume_summary = ""

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
        if _is_mock_company(raw_job["company"]):
            continue
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


def _refresh_job_search_query(db: Session, query: str, city: Optional[str], sort: str):
    return _job_search_query(db, query=query, city=city, sort=sort)


def _log_background_future_error(future):
    try:
        future.result()
    except Exception:
        _logger.exception("Background cover letter generation failed")


def _bg_generate_cover_letter(job_id, resume_text, company, role, job_description, source, job_url):
    dispatch_cover_letter_generation(job_id, resume_text, company, role, job_description, source, job_url)


def _expand_search_terms(query: str) -> List[str]:
    normalized = re.sub(r"\s+", " ", (query or "")).strip().lower()
    if not normalized:
        return []

    terms = {normalized}
    tokens = set(re.findall(r"[a-z0-9+#.]+", normalized))

    if "machine learning" in normalized or "ml" in tokens:
        terms.update({"machine learning", "machine learning engineer", "ml", "ai", "artificial intelligence", "data science"})

    if "artificial intelligence" in normalized or "ai" in tokens:
        terms.update({"artificial intelligence", "ai", "machine learning", "ml", "data science"})

    if "finance analyst" in normalized or "financial analyst" in normalized:
        terms.update({"finance analyst", "financial analyst", "accountant", "risk analyst", "investment banker"})

    if "marketing" in normalized:
        terms.update({"marketing", "marketing manager", "digital marketing", "brand manager", "seo specialist", "content writer"})

    if "sales" in normalized:
        terms.update({"sales", "sales representative", "business development", "account executive"})

    if any(token in normalized for token in ["software", "developer", "engineer", "full stack", "backend", "frontend", "devops", "qa", "mobile"]):
        terms.update({"software engineer", "frontend developer", "backend engineer", "full stack developer", "devops engineer", "qa engineer", "mobile developer"})

    return [term for term in terms if term]


def _job_search_query(db: Session, query: str, city: Optional[str], sort: str):
    search_query = _real_job_query(db.query(Job).filter(Job.is_active == True))
    terms = _expand_search_terms(query)
    if terms:
        conditions = []
        for term in terms:
            pattern = f"%{term}%"
            conditions.append(Job.title.ilike(pattern))
            conditions.append(Job.description.ilike(pattern))
        search_query = search_query.filter(or_(*conditions))
    if city:
        search_query = search_query.filter(func.lower(Job.city) == city.strip().lower())

    if sort == "newest":
        search_query = search_query.order_by(Job.scraped_at.desc().nullslast(), Job.fetched_at.desc().nullslast())
    else:
        search_query = search_query.order_by(Job.fetched_at.desc().nullslast())

    return search_query


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
    current_user = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    page = max(1, page)
    limit = max(1, min(100, limit))
    live_jobs: List[Job] = []

    if ENABLE_LIVE_SEARCH_FALLBACK:
        try:
            fetched_jobs = search_jobs(
                query=query,
                location=location,
                city=city,
                remote_only=remote_only,
                country_code=country_code,
                pakistan_only=pakistan_only,
            )
            if fetched_jobs:
                live_jobs = _upsert_jobs(db, fetched_jobs)
                db.commit()
        except Exception:
            db.rollback()
            _logger.exception("Live search failed; falling back to database results")

    if live_jobs:
        start = (page - 1) * limit
        items = live_jobs[start : start + limit]
    else:
        q = _refresh_job_search_query(db, query=query, city=city, sort=sort)
        items = q.offset((page - 1) * limit).limit(limit).all()

    profile = _get_selected_profile(db, current_user.id) if current_user else None
    content_scores: dict[int, float] = {}
    if profile:
        scored_items = []
        for job in items:
            score, include = _score_job_for_profile(job, profile)
            if include:
                scored_items.append((score, job))
                if getattr(job, "id", None) is not None:
                    content_scores[int(job.id)] = float(score)
        scored_items.sort(key=lambda pair: (pair[0], pair[1].id or 0), reverse=True)
        items = [job for _, job in scored_items]

    items = rerank_job_candidates(query, items, profile=profile, user_id=current_user.id if current_user else None, content_scores=content_scores)

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
        q = _real_job_query(db.query(Job).filter(Job.is_active == True))
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
    current_user = Depends(get_current_user_from_stream),
):
    import time as _time

    def _job_payload(j):
        return {
            "id": j.id,
            "title": j.title,
            "company": j.company,
            "description": j.description,
            "source": j.source,
            "url": j.url,
            "location": j.location,
            "salary": j.salary,
            "posted_date": j.posted_date,
        }

    def _emit(event: dict):
        return f"data: {json.dumps(event, ensure_ascii=False)}\n\n"

    def event_stream():
        start_time = _time.time()
        yield _emit({"status": "searching", "combined_count": 0, "elapsed": 0.0, "partial": []})

        def _source_calls():
            location_key = (location or "").strip().lower()
            selected_remote = remote_only or location_key == "remote"

            if selected_remote:
                return {
                    "remotive": lambda: [],
                    "jobicy": lambda: [],
                }

            source_map = {
                "rozee": lambda: fetch_rozee_pakistan(query, city or location, 1),
                "mustakbil": lambda: fetch_mustakbil_pakistan(query, city or location, 1),
                "bing": lambda: fetch_bing_pakistan(query, city or location, 1),
                "linkedin": lambda: fetch_linkedin_indexed(query, city or location, 4),
                "careers": lambda: fetch_company_careers(query, 6),
                "brightspyre": lambda: fetch_brightspyre(query, 1),
            }

            if location_key in {"karachi", "lahore", "islamabad", "rawalpindi", "faisalabad", "pakistan"} or pakistan_only or country_code.lower() == "pk":
                return source_map

            return {
                "rozee": lambda: fetch_rozee_pakistan(query, None, 1),
                "mustakbil": lambda: fetch_mustakbil_pakistan(query, None, 1),
                "bing": lambda: fetch_bing_pakistan(query, None, 1),
                "linkedin": lambda: fetch_linkedin_indexed(query, location or None, 4),
                "careers": lambda: fetch_company_careers(query, 6),
                "brightspyre": lambda: fetch_brightspyre(query, 1),
            }

        source_calls = _source_calls()
        if not source_calls:
            source_calls = {"fallback": lambda: search_jobs(query=query, location=location, city=city, remote_only=remote_only, country_code=country_code, pakistan_only=pakistan_only)}

        completed_jobs: List[Job] = []
        chunk_count = 0

        with ThreadPoolExecutor(max_workers=min(len(source_calls), 6) or 1) as executor:
            futures = {executor.submit(call): name for name, call in source_calls.items()}
            for future in concurrent.futures.as_completed(futures):
                source_name = futures[future]
                try:
                    source_jobs = future.result(timeout=0)
                except Exception as exc:
                    _logger.warning("search source failed: %s (%s)", source_name, exc)
                    source_jobs = []

                if not source_jobs and source_name == "fallback":
                    source_jobs = search_jobs(
                        query=query,
                        location=location,
                        city=city,
                        remote_only=remote_only,
                        country_code=country_code,
                        pakistan_only=pakistan_only,
                    )

                if not source_jobs:
                    elapsed = round(_time.time() - start_time, 1)
                    yield _emit({"partial": [], "source": source_name, "combined_count": chunk_count, "elapsed": elapsed})
                    continue

                saved_jobs = _upsert_jobs(db, source_jobs)
                completed_jobs.extend(saved_jobs)
                chunk = [_job_payload(j) for j in saved_jobs]
                chunk_count += len(chunk)
                elapsed = round(_time.time() - start_time, 1)
                yield _emit({"partial": chunk, "source": source_name, "combined_count": chunk_count, "elapsed": elapsed})

        final_query = _refresh_job_search_query(db, query=query, city=city, sort="newest")
        final_items = final_query.limit(100).all()
        final_payloads = [_job_payload(j) for j in final_items]
        yield _emit({"done": True, "results": final_payloads, "total": len(final_payloads), "elapsed": round(_time.time() - start_time, 1)})

    return StreamingResponse(event_stream(), media_type='text/event-stream')


@router.get("/sources")
def sources_status():
    return {"sources": get_pakistan_source_status()}


@router.get("/{job_id}/match", response_model=JobMatch)
def match_job(job_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        record_user_job_interaction(db, current_user.id, job_id, "view")
    except Exception:
        _logger.exception("Failed to record job view interaction")

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        return JobMatch(job_id=job_id, match_percentage=0, explanation="Job not found", missing_skills=[])

    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile or not profile.resume_text:
        return JobMatch(job_id=job_id, match_percentage=0, explanation="Upload resume first", missing_skills=[])

    resume_text = profile.resume_text or ""
    job_text = job.description or ""

    # Prefer stored skill arrays if present, otherwise extract on the fly
    job_skills = (getattr(job, "job_skills", None) or [])
    if not job_skills:
        job_skills = extract_skills(job_text, limit=50)

    profile_skills = parse_string_list(getattr(profile, "skills", None))
    if not profile_skills:
        profile_skills = extract_skills(resume_text, limit=50)

    try:
        explain = explain_match_for(
            {
                "id": job.id,
                "description": job_text,
                "experience_required": job.experience_required,
                "job_skills": job_skills,
            },
            {
                "id": profile.id,
                "resume_text": resume_text,
                "profile_skills": profile_skills,
            },
        )

        explanation_text = (
            f"Skills matched: {', '.join(explain.get('matching_skills') or [])}. "
            f"Missing: {', '.join(explain.get('missing_skills') or [])}. "
            f"{explain.get('experience_fit')}"
        )

        return JobMatch(
            job_id=job_id,
            match_percentage=float(explain.get("match_score", 0)),
            explanation=explanation_text,
            matched_skills=explain.get("matching_skills", []),
            missing_skills=explain.get("missing_skills", []),
        )
    except Exception:
        # Fallback to lightweight heuristic as before
        import re as _re

        def _words(text: str):
            return set([w for w in _re.findall(r"[a-zA-Z0-9+#.+]+", (text or "").lower()) if len(w) > 2])

        resume_words = _words(resume_text)
        job_words = _words(job_text)
        if not job_words:
            return JobMatch(job_id=job_id, match_percentage=0.0, explanation="No job description text to analyze", matched_skills=[], missing_skills=[])

        overlap = resume_words & job_words
        match_pct = int(min(100, (len(overlap) / max(1, len(job_words))) * 100))
        missing = sorted(list((job_words - resume_words)))[:12]
        matched = sorted(list(overlap))[:12]
        explanation = f"Heuristic match based on keyword overlap: {len(overlap)} of {len(job_words)} job keywords found in resume."
        return JobMatch(job_id=job_id, match_percentage=float(match_pct), explanation=explanation, matched_skills=matched, missing_skills=missing)


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
