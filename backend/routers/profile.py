import json
import os
import logging
import tempfile
import time
import re
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, Response, UploadFile
from starlette.background import BackgroundTask
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from backend.database import get_db, engine
from backend.models import Job, User, UserCertification, UserEducation, UserLanguage, UserPreference, UserProfile, UserProject, UserWorkExperience
from backend.security import get_current_user, require_current_user
from backend.schemas import ResumeBuildResponse, UserProfileListResponse, UserProfileOut, UserProfileSummary
from backend.services.profile_data import build_profile_resume_text, parse_int, parse_string_list, profile_completeness
from core.resume_analyzer import analyze_and_fix_resume, _extract_keywords, _keyword_hits, _score_resume
from core.resume_artifacts import save_resume_artifacts
from core.pdf_generator import generate_resume_pdf
from core.resume_template import render_resume_html
from core.resume_validator import validate_resume_output

logger = logging.getLogger(__name__)

_SKILL_OVERRIDES = {
    "sql": "SQL",
    "aws": "AWS",
    "gcp": "GCP",
    "git": "Git",
    "github": "GitHub",
    "fastapi": "FastAPI",
    "flask": "Flask",
    "django": "Django",
    "react": "React",
    "typescript": "TypeScript",
    "javascript": "JavaScript",
    "node.js": "Node.js",
    "data analysis": "Data Analysis",
    "machine learning": "Machine Learning",
    "deep learning": "Deep Learning",
    "power bi": "Power BI",
    "tableau": "Tableau",
    "rest api": "REST API",
    "rest apis": "REST API",
    "ci/cd": "CI/CD",
    "system design": "System Design",
    "problem solving": "Problem Solving",
    "communication": "Communication",
}

try:
    from ingest import chunk_text
except Exception:
    def chunk_text(text: str, chunk_size: int = 800, overlap: int = 200):
        if not text:
            return []
        step = max(1, chunk_size - overlap)
        chunks = []
        for start in range(0, len(text), step):
            chunk = text[start : start + chunk_size].strip()
            if chunk:
                chunks.append(chunk)
        return chunks


MAX_PROFILE_UPLOAD_BYTES = max(1, int(os.getenv("MAX_PROFILE_UPLOAD_BYTES", str(5 * 1024 * 1024))))
ALLOWED_RESUME_MIME_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}
RESUME_BUILD_CACHE_TTL_SECONDS = max(60, int(os.getenv("RESUME_BUILD_CACHE_TTL_SECONDS", "300")))
_RESUME_BUILD_CACHE: dict[tuple[int, int], tuple[float, dict]] = {}

router = APIRouter(tags=["Profile"], dependencies=[Depends(require_current_user)])
_preferences_table_ready = False


def _format_datetime(value) -> str | None:
    if value is None:
        return None
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return str(value)


def _ensure_user_preferences_table() -> None:
    global _preferences_table_ready
    if _preferences_table_ready:
        return

    try:
        inspector = inspect(engine)
        if not inspector.has_table(UserPreference.__tablename__):
            UserPreference.__table__.create(bind=engine, checkfirst=True)
        _preferences_table_ready = True
    except Exception:
        # keep runtime resilient; callers can still proceed without selected state
        pass


def _get_selected_preference(db: Session, user_id: int) -> UserPreference | None:
    _ensure_user_preferences_table()
    try:
        return db.query(UserPreference).filter(UserPreference.user_id == user_id).order_by(UserPreference.updated_at.desc(), UserPreference.id.desc()).first()
    except OperationalError:
        _ensure_user_preferences_table()
        try:
            return db.query(UserPreference).filter(UserPreference.user_id == user_id).order_by(UserPreference.updated_at.desc(), UserPreference.id.desc()).first()
        except Exception:
            return None


def _get_selected_profile_id(db: Session, user_id: int) -> int | None:
    preference = _get_selected_preference(db, user_id)
    if preference and preference.selected_profile_id:
        return int(preference.selected_profile_id)
    return None


def _set_selected_profile_id(db: Session, user_id: int, profile_id: int) -> None:
    _ensure_user_preferences_table()
    preference = _get_selected_preference(db, user_id)
    if not preference:
        preference = UserPreference(user_id=user_id, selected_profile_id=profile_id)
        db.add(preference)
    else:
        preference.selected_profile_id = profile_id
    db.commit()


def _clear_selected_profile_if_matches(db: Session, user_id: int, profile_id: int) -> None:
    _ensure_user_preferences_table()
    preference = _get_selected_preference(db, user_id)
    if preference and preference.selected_profile_id == profile_id:
        preference.selected_profile_id = None
        db.commit()


async def _load_profile_payload(request: Request) -> dict[str, Any]:
    content_type = (request.headers.get("content-type") or "").lower()
    if "application/json" in content_type:
        payload = await request.json()
        return payload if isinstance(payload, dict) else {}

    form = await request.form()
    payload: dict[str, Any] = {}
    for key, value in form.multi_items():
        if key in payload:
            existing = payload[key]
            if isinstance(existing, list):
                existing.append(value)
            else:
                payload[key] = [existing, value]
        else:
            payload[key] = value
    return payload


def _maybe_json_list(value: Any) -> list[dict[str, Any]]:
    if not value:
        return []
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except Exception:
            return []
    return []


def _pick_fields(item: dict[str, Any], allowed: list[str]) -> dict[str, Any]:
    return {key: item.get(key) for key in allowed if key in item}


def _profile_to_dict(profile: UserProfile) -> dict[str, Any]:
    return {
        "id": profile.id,
        "user_id": profile.user_id,
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.location,
        "linkedin_url": profile.linkedin_url,
        "portfolio_url": profile.portfolio_url,
        "summary": profile.summary,
        "skills": profile.skills or [],
        "achievements": profile.achievements or [],
        "preferred_job_titles": profile.preferred_job_titles or [],
        "desired_salary_min": profile.desired_salary_min,
        "desired_salary_max": profile.desired_salary_max,
        "willing_to_relocate": bool(profile.willing_to_relocate),
        "preferred_work_location": profile.preferred_work_location,
        "resume_text": profile.resume_text,
        "latest_ats_score": profile.latest_ats_score,
        "created_at": profile.created_at,
        "education": [
            {
                "id": item.id,
                "degree": item.degree,
                "institution": item.institution,
                "field_of_study": item.field_of_study,
                "start_year": item.start_year,
                "end_year": item.end_year,
                "gpa": item.gpa,
                "description": item.description,
            }
            for item in profile.education
        ],
        "work_experience": [
            {
                "id": item.id,
                "job_title": item.job_title,
                "company": item.company,
                "location": item.location,
                "start_date": item.start_date,
                "end_date": item.end_date,
                "responsibilities": item.responsibilities or [],
                "achievements": item.achievements or [],
            }
            for item in profile.work_experience
        ],
        "certifications": [
            {
                "id": item.id,
                "name": item.name,
                "issuing_org": item.issuing_org,
                "date_earned": item.date_earned,
                "credential_url": item.credential_url,
            }
            for item in profile.certifications
        ],
        "projects": [
            {
                "id": item.id,
                "name": item.name,
                "description": item.description,
                "technologies": item.technologies or [],
                "project_url": item.project_url,
            }
            for item in profile.projects
        ],
        "languages": [
            {
                "id": item.id,
                "name": item.name,
                "proficiency": item.proficiency,
            }
            for item in profile.languages
        ],
    }


def _profile_to_summary(profile: UserProfile) -> dict[str, Any]:
    data = _profile_to_dict(profile)
    return {
        "id": data["id"],
        "user_id": data["user_id"],
        "full_name": data["full_name"],
        "email": data["email"],
        "location": data["location"],
        "summary": data["summary"],
        "skills": data["skills"],
        "preferred_job_titles": data["preferred_job_titles"],
        "latest_ats_score": data["latest_ats_score"],
        "created_at": data["created_at"],
        "profile_completeness": profile_completeness(data),
    }


def _apply_profile_payload(profile: UserProfile, payload: dict[str, Any]) -> None:
    scalar_fields = [
        "full_name",
        "email",
        "phone",
        "location",
        "linkedin_url",
        "portfolio_url",
        "summary",
        "preferred_work_location",
        "resume_text",
    ]
    for field_name in scalar_fields:
        if field_name in payload:
            setattr(profile, field_name, payload.get(field_name) or None)

    for field_name in ["skills", "achievements", "preferred_job_titles"]:
        if field_name in payload:
            setattr(profile, field_name, parse_string_list(payload.get(field_name)))

    if "desired_salary_min" in payload:
        profile.desired_salary_min = parse_int(payload.get("desired_salary_min"))
    if "desired_salary_max" in payload:
        profile.desired_salary_max = parse_int(payload.get("desired_salary_max"))
    if "willing_to_relocate" in payload:
        profile.willing_to_relocate = str(payload.get("willing_to_relocate")).strip().lower() in {"1", "true", "yes", "on"}

    if "education" in payload:
        profile.education = [UserEducation(**_pick_fields(item, ["degree", "institution", "field_of_study", "start_year", "end_year", "gpa", "description"])) for item in _maybe_json_list(payload.get("education"))]
    if "work_experience" in payload:
        profile.work_experience = [
            UserWorkExperience(
                job_title=item.get("job_title"),
                company=item.get("company"),
                location=item.get("location"),
                start_date=item.get("start_date"),
                end_date=item.get("end_date"),
                responsibilities=parse_string_list(item.get("responsibilities")),
                achievements=parse_string_list(item.get("achievements")),
            )
            for item in _maybe_json_list(payload.get("work_experience"))
        ]
    if "certifications" in payload:
        profile.certifications = [UserCertification(**_pick_fields(item, ["name", "issuing_org", "date_earned", "credential_url"])) for item in _maybe_json_list(payload.get("certifications"))]
    if "projects" in payload:
        profile.projects = [
            UserProject(
                name=item.get("name"),
                description=item.get("description"),
                technologies=parse_string_list(item.get("technologies")),
                project_url=item.get("project_url"),
            )
            for item in _maybe_json_list(payload.get("projects"))
        ]
    if "languages" in payload:
        profile.languages = [UserLanguage(**_pick_fields(item, ["name", "proficiency"])) for item in _maybe_json_list(payload.get("languages"))]

    if not profile.resume_text:
        profile.resume_text = build_profile_resume_text(profile)


def _refresh_profile_resume_text(profile: UserProfile) -> str:
    profile.resume_text = build_profile_resume_text(profile)
    return profile.resume_text


async def _validate_resume_upload(upload: UploadFile) -> None:
    filename = (upload.filename or "").lower()
    content_type = (upload.content_type or "").lower()
    suffix = Path(filename).suffix

    if suffix not in ALLOWED_RESUME_EXTENSIONS and content_type not in ALLOWED_RESUME_MIME_TYPES:
        raise HTTPException(status_code=415, detail="Resume must be a PDF or DOCX file")

    content = await upload.read(MAX_PROFILE_UPLOAD_BYTES + 1)
    if len(content) > MAX_PROFILE_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="Resume file must be 5 MB or smaller")
    await upload.seek(0)


async def _index_profile_text(profile_text: str, user_id: int) -> None:
    try:
        from core.rag_service import get_chroma_collection, get_embedding_model

        collection = get_chroma_collection()
        if collection is None:
            return

        chunks = chunk_text(profile_text, chunk_size=800, overlap=200)
        if not chunks:
            return

        ids = []
        metadatas = []
        documents = []
        for i, chunk in enumerate(chunks):
            ids.append(f"profile_{user_id}_{i}")
            metadatas.append({"doc_type": "user_profile", "user_id": str(user_id), "chunk_index": i})
            documents.append(chunk)

        try:
            embedding_model = get_embedding_model()
        except Exception:
            embedding_model = None

        if embedding_model is not None:
            try:
                import asyncio

                loop = asyncio.get_running_loop()
                embeddings = await loop.run_in_executor(
                    None,
                    lambda: embedding_model.encode(documents, convert_to_numpy=True),
                )
            except RuntimeError:
                embeddings = embedding_model.encode(documents, convert_to_numpy=True)

            embeddings_payload = [embedding.tolist() for embedding in embeddings]
            try:
                collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings_payload)
            except Exception:
                try:
                    collection.upsert(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings_payload)
                except Exception:
                    pass
            return

        try:
            collection.add(ids=ids, documents=documents, metadatas=metadatas)
        except Exception:
            try:
                collection.upsert(ids=ids, documents=documents, metadatas=metadatas)
            except Exception:
                pass
    except Exception:
        return


def _extract_text_from_upload(upload: UploadFile) -> str:
    fname = upload.filename.lower() if upload and upload.filename else ''
    data = b''
    try:
        data = upload.file.read()
    finally:
        try:
            upload.file.seek(0)
        except Exception:
            pass

    if fname.endswith('.pdf'):
        try:
            from pypdf import PdfReader
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(data)
                tmp.flush()
                tmp_path = tmp.name
            reader = PdfReader(tmp_path)
            pages = []
            for p in reader.pages:
                try:
                    pages.append(p.extract_text() or '')
                except Exception:
                    continue
            os.unlink(tmp_path)
            return '\n'.join(pages)
        except Exception:
            return ''

    if fname.endswith('.docx'):
        try:
            import docx2txt
            with tempfile.NamedTemporaryFile(delete=False, suffix='.docx') as tmp:
                tmp.write(data)
                tmp.flush()
                tmp_path = tmp.name
            text = docx2txt.process(tmp_path) or ''
            os.unlink(tmp_path)
            return text
        except Exception:
            return ''

    # fallback: treat as plain text
    try:
        return data.decode('utf-8', errors='ignore')
    except Exception:
        return ''


def _load_active_profile(db: Session, user_id: int) -> UserProfile | None:
    selected_id = _get_selected_profile_id(db, user_id)
    if selected_id:
        selected = db.query(UserProfile).filter(UserProfile.id == selected_id, UserProfile.user_id == user_id).first()
        if selected:
            return selected
    return db.query(UserProfile).filter(UserProfile.user_id == user_id).order_by(UserProfile.created_at.desc(), UserProfile.id.desc()).first()


def _build_default_resume_text(profile: UserProfile | None, job: Job | None) -> str:
    if profile:
        return build_profile_resume_text(profile, job_title=getattr(job, "title", None), company=getattr(job, "company", None))
    job_title = getattr(job, "title", None) or "the target role"
    company = getattr(job, "company", None) or "the employer"
    return f"Summary\nTailored for {job_title} at {company}."


def _get_cached_resume_build(user_id: int, job_id: int) -> dict | None:
    cache_key = (user_id, job_id)
    cached = _RESUME_BUILD_CACHE.get(cache_key)
    if not cached:
        return None
    expires_at, payload = cached
    if expires_at < time.time():
        _RESUME_BUILD_CACHE.pop(cache_key, None)
        return None
    return payload


def _set_cached_resume_build(user_id: int, job_id: int, payload: dict) -> None:
    _RESUME_BUILD_CACHE[(user_id, job_id)] = (time.time() + RESUME_BUILD_CACHE_TTL_SECONDS, payload)


@router.post('/build_resume/{job_id}', response_model=ResumeBuildResponse)
def build_resume(job_id: int, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # Allow callers (tests/debug) to bypass the in-memory cache by sending X-Force-Rebuild: 1
    force_rebuild = str((request.headers.get("x-force-rebuild") or "")).strip().lower() in {"1", "true", "yes"}
    cached = None if force_rebuild else _get_cached_resume_build(current_user.id, job_id)
    if cached:
        return ResumeBuildResponse(**{**cached, "cached": True})

    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    profile = _load_active_profile(db, current_user.id)
    source_resume_text = _build_default_resume_text(profile, job)
    if profile and profile.resume_text and not profile.skills and not profile.education and not profile.work_experience:
        source_resume_text = profile.resume_text.strip()

    profile_data = _profile_to_dict(profile) if profile else {}

    # Build structured profile data to give the resume analyzer richer context
    profile_payload = None
    if profile:
        profile_payload = {
            "full_name": profile_data.get("full_name"),
            "email": profile_data.get("email"),
            "phone": profile_data.get("phone"),
            "location": profile_data.get("location"),
            # ensure skills are normalized as a list of trimmed strings
            "skills": [s.strip() for s in (profile_data.get("skills") or []) if str(s).strip()],
            # also include a CSV form for callers that expect a single string
            "skills_csv": ", ".join([s.strip() for s in (profile_data.get("skills") or []) if str(s).strip()]),
            "achievements": profile_data.get("achievements") or [],
            "work_experience": profile_data.get("work_experience") or [],
            "education": profile_data.get("education") or [],
            "projects": profile_data.get("projects") or [],
            "certifications": profile_data.get("certifications") or [],
            "languages": profile_data.get("languages") or [],
            "resume_text": profile.get("resume_text") if isinstance(profile, dict) else getattr(profile, "resume_text", None),
        }

    job_description = job.description or ""
    job_keywords = _extract_keywords(job_description)

    analyzed = analyze_and_fix_resume(source_resume_text, job_description, structured_profile=profile_payload, job_title=job.title if job else None)
    if isinstance(analyzed, str):
        analyzed = {"fixed_resume_text": analyzed, "sections": {}, "ats_score": 0, "changes_made": []}
    elif not isinstance(analyzed, dict):
        analyzed = {}

    fixed_resume_text = analyzed.get("fixed_resume_text") or analyzed.get("enhanced_resume_text") or source_resume_text
    matched_keywords = sorted(_keyword_hits(fixed_resume_text, job_keywords))
    missing_keywords = [keyword for keyword in job_keywords if keyword not in matched_keywords]
    ats_score = int(analyzed.get("ats_score") or _score_resume(fixed_resume_text, job_description, job_keywords, missing_keywords))
    analyzed["ats_score"] = ats_score
    analyzed["keyword_debug"] = {
        "job_keywords": job_keywords[:15],
        "matched_keywords": matched_keywords[:15],
        "missing_keywords": missing_keywords[:15],
    }

    # Build a normalized structured resume payload for HTML rendering.
    analyzer_sections = analyzed.get("sections") or {}
    experience_items = []
    for item in profile_data.get("work_experience") or []:
        if not isinstance(item, dict):
            continue
        bullets = []
        for value in (item.get("achievements") or []):
            text = str(value or "").strip()
            if text:
                bullets.append(text)
        for value in (item.get("responsibilities") or []):
            text = str(value or "").strip()
            if text:
                bullets.append(text)
        if not bullets and fixed_resume_text:
            bullets = [line.lstrip("-• ").strip() for line in fixed_resume_text.splitlines() if line.lstrip().startswith(("-", "•"))][:4]
        experience_items.append({
            "title": item.get("job_title") or item.get("title") or "Experience",
            "organization": item.get("company") or "",
            "year": " - ".join([str(item.get("start_date") or "").strip(), str(item.get("end_date") or "").strip()]).strip(" -"),
            "bullets": bullets[:5],
        })

    education_items = []
    for item in profile_data.get("education") or []:
        if not isinstance(item, dict):
            continue
        header_bits = [item.get("degree"), item.get("institution")]
        education_items.append({
            "title": " • ".join([bit for bit in header_bits if bit]),
            "organization": "",
            "year": " - ".join([str(item.get("start_year") or "").strip(), str(item.get("end_year") or "").strip()]).strip(" -"),
            "bullets": [bit for bit in [f"GPA: {item.get('gpa')}" if item.get('gpa') else "", item.get("field_of_study") or ""] if bit],
        })

    project_items = []
    for item in profile_data.get("projects") or []:
        if not isinstance(item, dict):
            continue
        techs = ", ".join(item.get("technologies") or [])
        bullets = []
        if item.get("description"):
            bullets.append(str(item.get("description")))
        if techs:
            bullets.append(f"Technologies: {techs}")
        project_items.append({
            "title": item.get("name") or "Project",
            "organization": "",
            "year": "",
            "bullets": bullets,
        })

    certification_items = []
    for item in profile_data.get("certifications") or []:
        if not isinstance(item, dict):
            continue
        certification_items.append({
            "title": item.get("name") or "Certification",
            "organization": item.get("issuing_org") or "",
            "year": item.get("date_earned") or "",
            "bullets": [],
        })

    language_items = []
    for item in profile_data.get("languages") or []:
        if not isinstance(item, dict):
            continue
        language_items.append(f"{item.get('name') or 'Language'} | {item.get('proficiency') or ''}".strip(" |"))

    achievement_items = profile_data.get("achievements") or []
    html_resume = render_resume_html(
        {
            "candidate_name": profile_data.get("full_name") or getattr(current_user, "name", None) or "Tailored Resume",
            "tagline": f"Tailored for {job.title or 'the role'} at {job.company or 'the company'}",
            "contact_lines": [line for line in [profile_data.get("email") or current_user.email, profile_data.get("phone"), profile_data.get("location"), profile_data.get("linkedin_url"), profile_data.get("portfolio_url")] if line],
            "summary": analyzer_sections.get("summary") or profile_data.get("summary") or "",
            "skills": analyzer_sections.get("skills") or profile_data.get("skills") or [],
            "experience": experience_items,
            "education": education_items,
            "projects": project_items,
            "certifications": certification_items,
            "languages": language_items,
            "achievements": analyzer_sections.get("achievements") or achievement_items or [],
            "ats_score": ats_score,
            "validation_message": "",
        }
    )

    validation = validate_resume_output(fixed_resume_text, html_resume, job.description or "")
    if not validation.get("passed"):
        logger.warning("Resume validation warning for user %s job %s: %s", current_user.id, job_id, "; ".join(validation.get("warnings") or []))

    html_resume = render_resume_html(
        {
            "candidate_name": profile_data.get("full_name") or getattr(current_user, "name", None) or "Tailored Resume",
            "tagline": f"Tailored for {job.title or 'the role'} at {job.company or 'the company'}",
            "contact_lines": [line for line in [profile_data.get("email") or current_user.email, profile_data.get("phone"), profile_data.get("location"), profile_data.get("linkedin_url"), profile_data.get("portfolio_url")] if line],
            "summary": analyzer_sections.get("summary") or profile_data.get("summary") or "",
            "skills": analyzer_sections.get("skills") or profile_data.get("skills") or [],
            "experience": experience_items,
            "education": education_items,
            "projects": project_items,
            "certifications": certification_items,
            "languages": language_items,
            "achievements": analyzer_sections.get("achievements") or achievement_items or [],
            "ats_score": ats_score,
            "validation_message": validation.get("message") or "",
        }
    )

    response_sections = {
        "summary": [analyzer_sections.get("summary") or profile_data.get("summary") or ""],
        "skills": analyzer_sections.get("skills") or profile_data.get("skills") or [],
        "experience": experience_items,
        "education": education_items,
        "projects": project_items,
        "certifications": certification_items,
        "languages": language_items,
    }

    save_resume_artifacts(
        job_id,
        source_resume_text,
        fixed_resume_text,
        html_resume,
        analyzed.get("changes_made") or [],
        metadata={
            "user_id": current_user.id,
            "job_title": job.title,
            "company": job.company,
            "ats_score": ats_score,
            "validation": validation,
            "keyword_debug": analyzed.get("keyword_debug"),
        },
    )

    if profile:
        try:
            profile.latest_ats_score = float(ats_score)
            db.commit()
        except Exception:
            db.rollback()

    payload = {
        "original_resume": source_resume_text,
        "simple_text_version": fixed_resume_text,
        "fixed_resume_text": fixed_resume_text,
        "sections": response_sections,
        "keyword_debug": analyzed.get("keyword_debug") or {},
        "ats_score": ats_score,
        "changes_made": analyzed.get("changes_made") or [],
        "html_resume": html_resume,
        "validation_passed": bool(validation.get("passed")),
        "validation_message": validation.get("message") or "",
        "cached": False,
    }
    _set_cached_resume_build(current_user.id, job_id, payload)
    return ResumeBuildResponse(**payload)


@router.get('/build_resume/{job_id}/pdf')
def download_resume_pdf(job_id: int, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    resume_payload = build_resume(job_id, request, current_user, db)
    pdf_path = None
    try:
        # try to use structured sections if available, otherwise fall back to raw text
        sections = getattr(resume_payload, "sections", None) or {}

        # Try to get candidate metadata from the user's selected profile or current_user
        profile = _load_active_profile(db, current_user.id)
        candidate_name = None
        contact_lines = []
        if profile:
            candidate_name = getattr(profile, "full_name", None) or getattr(current_user, "name", None)
            if getattr(profile, "email", None):
                contact_lines.append(profile.email)
            if getattr(profile, "phone", None):
                contact_lines.append(profile.phone)
            if getattr(profile, "location", None):
                contact_lines.append(profile.location)
            if getattr(profile, "linkedin_url", None):
                contact_lines.append(profile.linkedin_url)
            if getattr(profile, "portfolio_url", None):
                contact_lines.append(profile.portfolio_url)
        else:
            candidate_name = getattr(current_user, "name", None) or getattr(current_user, "email", None)
            if getattr(current_user, "email", None):
                contact_lines.append(current_user.email)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            pdf_path = temp_file.name

        if sections:
            generate_resume_pdf(sections, pdf_path, candidate_name=candidate_name, contact_lines=contact_lines)
        else:
            # fallback to raw text
            generate_resume_pdf(resume_payload.fixed_resume_text or resume_payload.simple_text_version or resume_payload.original_resume, pdf_path, candidate_name=candidate_name, contact_lines=contact_lines)

        with open(pdf_path, 'rb') as pdf_file:
            pdf_bytes = pdf_file.read()

        filename = f"tailored_resume_job_{job_id}.pdf"
        return Response(
            content=pdf_bytes,
            media_type='application/pdf',
            headers={'Content-Disposition': f'attachment; filename="{filename}"'},
        )
    finally:
        if pdf_path:
            try:
                os.unlink(pdf_path)
            except Exception:
                pass


@router.post('/profile')
async def upload_profile(request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payload = await _load_profile_payload(request)

    if not payload.get("education") and payload.get("degree"):
        payload["education"] = [
            {
                "degree": payload.get("degree"),
                "institution": payload.get("institution"),
                "field_of_study": payload.get("field_of_study"),
                "gpa": payload.get("gpa"),
            }
        ]

    if not payload.get("summary") and payload.get("years_experience"):
        payload["summary"] = f"{payload.get('years_experience')} years of experience."

    resume_upload = payload.get("resume")
    resume_text = ""
    if isinstance(resume_upload, UploadFile):
        await _validate_resume_upload(resume_upload)
        resume_text = _extract_text_from_upload(resume_upload)
        payload["resume_text"] = resume_text or payload.get("resume_text")

    new_profile = UserProfile(user_id=current_user.id)
    _apply_profile_payload(new_profile, payload)
    _refresh_profile_resume_text(new_profile)

    db.add(new_profile)
    db.commit()
    db.refresh(new_profile)

    if os.getenv("ENABLE_PROFILE_INDEXING", "").strip().lower() in {"1", "true", "yes", "on"}:
        await _index_profile_text(new_profile.resume_text or "", current_user.id)

    return {"status": "success", "message": "Profile saved", "profile": _profile_to_dict(new_profile)}


@router.get('/profile')
def profile_list(page: int = 1, per_page: int = 10, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        query = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).order_by(UserProfile.created_at.desc(), UserProfile.id.desc())
        total = query.count()
        rows = query.offset((page - 1) * per_page).limit(per_page).all()
        profiles = [_profile_to_summary(row) for row in rows]
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to list profiles")

    selected_id = _get_selected_profile_id(db, current_user.id)
    selected_profile = None
    if selected_id:
        selected_row = db.query(UserProfile).filter(UserProfile.id == selected_id, UserProfile.user_id == current_user.id).first()
        if selected_row:
            selected_profile = _profile_to_dict(selected_row)
        else:
            _clear_selected_profile_if_matches(db, current_user.id, selected_id)
            selected_id = None

    exists = total > 0
    response = UserProfileListResponse(profiles=profiles, selected_profile_id=selected_id, selected_profile=selected_profile).model_dump()
    response.update({"exists": exists, "page": page, "per_page": per_page, "total": total})
    return response


@router.post('/profile/select/{profile_id}')
def select_profile(profile_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        profile = db.query(UserProfile).filter(UserProfile.id == profile_id, UserProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        _set_selected_profile_id(db, current_user.id, profile_id)
        return {"status": "success", "selected_profile_id": profile_id}
    except Exception:
        raise


@router.post('/profile/select')
def select_profile_legacy(payload: dict = Body(...), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        pid = int(payload.get('profile_id'))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid profile_id")

    profile = db.query(UserProfile).filter(UserProfile.id == pid, UserProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    _set_selected_profile_id(db, current_user.id, pid)
    return {"status": "success", "selected_profile_id": pid}


@router.get('/profile/selected')
def get_selected_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    selected_id = _get_selected_profile_id(db, current_user.id)
    if not selected_id:
        return {"selected_profile_id": None, "profile": None}

    profile = db.query(UserProfile).filter(UserProfile.id == selected_id, UserProfile.user_id == current_user.id).first()
    if not profile:
        return {"selected_profile_id": None, "profile": None}

    return {
        "selected_profile_id": profile.id,
        "profile": _profile_to_dict(profile),
    }

@router.get('/profile/{profile_id}')
def get_profile(profile_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        profile = db.query(UserProfile).filter(UserProfile.id == profile_id, UserProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        result = _profile_to_dict(profile)
        result["profile_completeness"] = profile_completeness(result)
        return result
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to load profile")


@router.delete('/profile/{profile_id}')
def delete_profile(profile_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        profile = db.query(UserProfile).filter(UserProfile.id == profile_id, UserProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")
        db.delete(profile)
        db.commit()
        _clear_selected_profile_if_matches(db, current_user.id, profile_id)
        return {"status": "success"}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Delete failed")

@router.patch('/profile/{profile_id}')
async def update_profile(profile_id: int, request: Request, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        profile = db.query(UserProfile).filter(UserProfile.id == profile_id, UserProfile.user_id == current_user.id).first()
        if not profile:
            raise HTTPException(status_code=404, detail="Profile not found")

        payload = await _load_profile_payload(request)
        if not payload.get("education") and payload.get("degree"):
            payload["education"] = [
                {
                    "degree": payload.get("degree"),
                    "institution": payload.get("institution"),
                    "field_of_study": payload.get("field_of_study"),
                    "gpa": payload.get("gpa"),
                }
            ]
        if not payload.get("summary") and payload.get("years_experience"):
            payload["summary"] = f"{payload.get('years_experience')} years of experience."

        resume_upload = payload.get("resume")
        if isinstance(resume_upload, UploadFile):
            await _validate_resume_upload(resume_upload)
            payload["resume_text"] = _extract_text_from_upload(resume_upload)

        _apply_profile_payload(profile, payload)
        _refresh_profile_resume_text(profile)
        db.commit()
        db.refresh(profile)
        return {"status": "success", "message": "Profile updated", "profile": _profile_to_dict(profile)}
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Update failed")




