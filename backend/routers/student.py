from __future__ import annotations

import os
from datetime import datetime, timedelta
from collections import defaultdict
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Integer, and_, exists, func, inspect, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from backend.database import engine, get_db
from backend.models import Program, Scholarship, SavedProgram, StudentProfile, StudyApplication, University, UniversityMatchCache, User, UserPreference
from backend.security import get_current_user
import threading
import os

# Allow disabling indexing during local/dev runs to avoid slow LLM/embedding calls
DISABLE_INDEXING = os.getenv('DISABLE_INDEXING', '').strip().lower() == 'true'
from backend.security import require_current_user
from backend.schemas import (
    ProgramOut,
    ScholarshipOut,
    SavedProgramOut,
    UniversityDetailResponse,
    UniversityFilterResponse,
    UniversityProgramGroup,
    StudentProfileCreate,
    StudentProfileListResponse,
    StudentProfileOut,
    StudentProfileUpdate,
    StudentProgramMatchOut,
    StudentApplyRequest,
    StudentSaveRequest,
    StudyApplicationOut,
    StudyApplicationUpdate,
    UniversityOut,
    UniversityMatchDetailResponse,
    UniversityMatchProgramItem,
    UniversityMatchRecommendRequest,
    UniversityMatchRecommendResponse,
    UniversityRecommendationItem,
    UniversityRecommendationRequest,
    UniversityRecommendationResponse,
)

router = APIRouter(prefix="/student", tags=["Student Recommender"], dependencies=[Depends(require_current_user)])
api_router = APIRouter(prefix="/api/student", tags=["Student Search"], dependencies=[Depends(require_current_user)])

MATCH_CACHE_TTL_DAYS = 7
logger = logging.getLogger(__name__)
_student_preferences_ready = False


def _match_service():
    from backend.services import university_match_service as service

    return service


def _profile_to_dict(profile: StudentProfile) -> dict:
    return {
        "id": profile.id,
        "gpa": profile.gpa,
        "gre_score": profile.gre_score,
        "toefl_score": profile.toefl_score,
        "ielts_score": profile.ielts_score,
        "budget_per_year": profile.budget_per_year,
        "preferred_countries": profile.preferred_countries or [],
        "intended_major": profile.intended_major,
        "degree_level": profile.degree_level,
        "academic_background": profile.academic_background,
    }


def _ensure_student_preferences_storage() -> None:
    global _student_preferences_ready
    if _student_preferences_ready:
        return

    try:
        inspector = inspect(engine)
        if not inspector.has_table(UserPreference.__tablename__):
            UserPreference.__table__.create(bind=engine, checkfirst=True)
            inspector = inspect(engine)

        columns = {column["name"] for column in inspector.get_columns(UserPreference.__tablename__)}
        if "selected_student_profile_id" not in columns:
            with engine.begin() as connection:
                connection.exec_driver_sql(f"ALTER TABLE {UserPreference.__tablename__} ADD COLUMN selected_student_profile_id INTEGER")
        _student_preferences_ready = True
    except Exception:
        pass


def _get_selected_student_preference(db: Session, user_id: int) -> UserPreference | None:
    _ensure_student_preferences_storage()
    try:
        return (
            db.query(UserPreference)
            .filter(UserPreference.user_id == user_id)
            .order_by(UserPreference.updated_at.desc(), UserPreference.id.desc())
            .first()
        )
    except Exception:
        return None


def _get_selected_student_profile_id(db: Session, user_id: int) -> int | None:
    preference = _get_selected_student_preference(db, user_id)
    if preference and preference.selected_student_profile_id:
        return int(preference.selected_student_profile_id)
    return None


def _set_selected_student_profile_id(db: Session, user_id: int, profile_id: int) -> None:
    _ensure_student_preferences_storage()
    preference = _get_selected_student_preference(db, user_id)
    if not preference:
        preference = UserPreference(user_id=user_id, selected_student_profile_id=profile_id)
        db.add(preference)
    else:
        preference.selected_student_profile_id = profile_id
    db.commit()


def _clear_selected_student_profile_if_matches(db: Session, user_id: int, profile_id: int) -> None:
    _ensure_student_preferences_storage()
    preference = _get_selected_student_preference(db, user_id)
    if preference and preference.selected_student_profile_id == profile_id:
        preference.selected_student_profile_id = None
        db.commit()


def _program_to_dict(program: Program) -> dict:
    return {
        "id": program.id,
        "university_id": program.university_id,
        "name": program.name,
        "degree_level": program.degree_level,
        "duration_years": program.duration_years,
        "estimated_tuition_fees": program.estimated_tuition_fees,
        "currency": program.currency,
        "min_gpa": program.min_gpa,
    }


def _university_to_dict(university: University) -> dict:
    return {
        "id": university.id,
        "name": university.name,
        "country": university.country,
        "city": university.city,
        "website": university.website,
        "ranking": university.ranking,
        "ranking_global": university.ranking_global,
        "logo_url": university.logo_url,
        "acceptance_rate": university.acceptance_rate,
        "accreditation": university.accreditation,
        "student_population": university.student_population,
    }


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    try:
        return int(str(value).strip())
    except Exception:
        return None


def _normalized_like(value: str) -> str:
    return f"%{value.strip().lower()}%"


def _university_ranking_value(university: University) -> Optional[int]:
    if university.ranking_global is not None:
        return university.ranking_global
    parsed = _safe_int(university.ranking)
    return parsed


def _program_passes_filters(
    program: Program,
    university: University,
    degree_level: Optional[str],
    intake: Optional[str],
    max_tuition: Optional[int],
    scholarship_only: bool,
) -> bool:
    if degree_level and degree_level.strip().lower() not in program.degree_level.lower():
        return False
    if intake and (program.semester_intake or "").strip():
        if intake.strip().lower() not in program.semester_intake.lower():
            return False
    if max_tuition is not None and program.estimated_tuition_fees > max_tuition:
        return False
    if scholarship_only and not (program.scholarship_available or university.scholarships):
        return False
    return True


@api_router.get("/universities/filter", response_model=UniversityFilterResponse)
def filter_universities(
    country: Optional[str] = None,
    min_ranking: Optional[int] = None,
    max_tuition: Optional[int] = None,
    degree_level: Optional[str] = None,
    intake: Optional[str] = None,
    scholarship_only: bool = False,
    page: int = 1,
    limit: int = 20,
    db: Session = Depends(get_db),
):
    if page < 1 or limit < 1:
        raise HTTPException(status_code=422, detail="page and limit must be positive integers")

    try:
        university_query = select(
            University.id,
            University.name,
            University.country,
            University.city,
            University.website,
            University.ranking,
            University.ranking_global,
            University.logo_url,
            University.acceptance_rate,
            University.accreditation,
            University.student_population,
        )
        if country:
            university_query = university_query.where(func.lower(University.country) == country.strip().lower())
        if min_ranking is not None:
            university_query = university_query.where(
                or_(
                    University.ranking_global <= min_ranking,
                    and_(University.ranking_global.is_(None), func.cast(University.ranking, Integer) <= min_ranking),
                )
            )
        if scholarship_only:
            university_query = university_query.where(
                exists().where(Scholarship.university_id == University.id)
            )

        university_query = university_query.order_by(University.country.asc(), University.name.asc())
        university_rows = db.execute(university_query).mappings().all()
    except SQLAlchemyError:
        logger.exception("University filter query failed")
        raise HTTPException(
            status_code=503,
            detail="University search is temporarily unavailable due to a database issue.",
        )
    if not university_rows:
        return UniversityFilterResponse(page=page, limit=limit, total=0, items=[])

    university_ids = [row["id"] for row in university_rows]
    try:
        program_query = select(
            Program.id,
            Program.university_id,
            Program.name,
            Program.degree_level,
            Program.duration_years,
            Program.estimated_tuition_fees,
            Program.currency,
            Program.min_gpa,
            Program.ranking_global,
            Program.ranking_national,
            Program.min_ielts,
            Program.min_toefl,
            Program.application_deadline,
            Program.semester_intake,
            Program.living_cost_estimate,
            Program.scholarship_available,
            Program.program_url,
        ).where(Program.university_id.in_(university_ids))
        if degree_level:
            program_query = program_query.where(func.lower(Program.degree_level).contains(degree_level.strip().lower()))
        if intake and intake.strip():
            program_query = program_query.where(func.lower(Program.semester_intake).contains(intake.strip().lower()))
        if max_tuition is not None:
            program_query = program_query.where(Program.estimated_tuition_fees <= max_tuition)
        program_rows = db.execute(program_query).mappings().all()
    except SQLAlchemyError:
        logger.exception("Program filter query failed")
        raise HTTPException(
            status_code=503,
            detail="University search is temporarily unavailable due to a database issue.",
        )

    programs_by_university_id: Dict[int, List[ProgramOut]] = defaultdict(list)
    for program_row in program_rows:
        programs_by_university_id[program_row["university_id"]].append(ProgramOut.model_validate(program_row))

    items: List[UniversityProgramGroup] = []
    for university_row in university_rows:
        matching_programs = programs_by_university_id.get(university_row["id"], [])
        if not matching_programs:
            continue
        items.append(
            UniversityProgramGroup(
                university=UniversityOut.model_validate(university_row),
                programs=matching_programs,
            )
        )

    total = len(items)
    start = (page - 1) * limit
    end = start + limit
    return UniversityFilterResponse(page=page, limit=limit, total=total, items=items[start:end])


@api_router.get("/university/{university_id}/detail", response_model=UniversityDetailResponse)
def university_detail(university_id: int, db: Session = Depends(get_db)):
    university = (
        db.query(University)
        .options(selectinload(University.programs), selectinload(University.scholarships))
        .filter(University.id == university_id)
        .first()
    )
    if not university:
        raise HTTPException(status_code=404, detail="University not found")

    programs = sorted(university.programs, key=lambda item: (item.degree_level.lower(), item.name.lower()))
    scholarships = sorted(university.scholarships, key=lambda item: (item.deadline or "", item.name.lower()))
    return UniversityDetailResponse(
        university=UniversityOut.model_validate(university),
        programs=[ProgramOut.model_validate(program) for program in programs],
        scholarships=[ScholarshipOut.model_validate(scholarship) for scholarship in scholarships],
    )


def _cache_lookup(db: Session, user_id: int, student_profile_id: int, program_id: int, intended_major: str) -> UniversityMatchCache | None:
    now = datetime.utcnow()
    cache = (
        db.query(UniversityMatchCache)
        .filter(
            UniversityMatchCache.user_id == user_id,
            UniversityMatchCache.student_profile_id == student_profile_id,
            UniversityMatchCache.program_id == program_id,
            UniversityMatchCache.intended_major == intended_major,
            UniversityMatchCache.expires_at > now,
        )
        .first()
    )
    return cache


@router.post("/profile", response_model=StudentProfileOut)
@api_router.post("/profile", response_model=StudentProfileOut)
def create_student_profile(payload: StudentProfileCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = StudentProfile(
        user_id=current_user.id,
        gpa=payload.gpa,
        gre_score=payload.gre_score,
        toefl_score=payload.toefl_score,
        ielts_score=payload.ielts_score,
        budget_per_year=payload.budget_per_year,
        preferred_countries=payload.preferred_countries or [],
        intended_major=payload.intended_major,
        degree_level=payload.degree_level,
        academic_background=payload.academic_background,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    _set_selected_student_profile_id(db, current_user.id, profile.id)
    # Index embeddings asynchronously to avoid blocking the request on slow
    # embedding/model calls. Run in a daemon thread so the request returns
    # promptly even when the vector DB or LLM provider is slow or unavailable.
    try:
        if not DISABLE_INDEXING:
            threading.Thread(target=_match_service().index_student_profile_embedding, args=(profile,), daemon=True).start()
    except Exception:
        pass
    return profile


@api_router.get("/profile", response_model=StudentProfileOut)
def get_current_student_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    selected_id = _get_selected_student_profile_id(db, current_user.id)
    profile = None
    if selected_id:
        profile = db.query(StudentProfile).filter(StudentProfile.id == selected_id, StudentProfile.user_id == current_user.id).first()
    if not profile:
        profile = db.query(StudentProfile).filter(StudentProfile.user_id == current_user.id).order_by(StudentProfile.created_at.desc(), StudentProfile.id.desc()).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return profile


@router.get("/profiles", response_model=StudentProfileListResponse)
@api_router.get("/profiles", response_model=StudentProfileListResponse)
def list_student_profiles(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profiles = (
        db.query(StudentProfile)
        .filter(StudentProfile.user_id == current_user.id)
        .order_by(StudentProfile.created_at.desc(), StudentProfile.id.desc())
        .all()
    )
    selected_id = _get_selected_student_profile_id(db, current_user.id)
    if selected_id and not any(profile.id == selected_id for profile in profiles):
        _clear_selected_student_profile_if_matches(db, current_user.id, selected_id)
        selected_id = None
    return StudentProfileListResponse(
        selected_profile_id=selected_id,
        profiles=[StudentProfileOut.model_validate(profile) for profile in profiles],
    )


@router.post("/profile/select/{profile_id}")
@api_router.post("/profile/select/{profile_id}")
def select_student_profile(profile_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id, StudentProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    _set_selected_student_profile_id(db, current_user.id, profile_id)
    return {"status": "success", "selected_profile_id": profile_id}


@router.delete("/profile/{profile_id}")
@api_router.delete("/profile/{profile_id}")
def delete_student_profile(profile_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id, StudentProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    db.delete(profile)
    db.commit()
    _clear_selected_student_profile_if_matches(db, current_user.id, profile_id)

    next_selected = _get_selected_student_profile_id(db, current_user.id)
    if not next_selected:
        fallback = (
            db.query(StudentProfile)
            .filter(StudentProfile.user_id == current_user.id)
            .order_by(StudentProfile.created_at.desc(), StudentProfile.id.desc())
            .first()
        )
        if fallback:
            _set_selected_student_profile_id(db, current_user.id, fallback.id)
            next_selected = fallback.id

    return {"status": "success", "selected_profile_id": next_selected}


@router.patch("/profile/{profile_id}", response_model=StudentProfileOut)
@api_router.patch("/profile/{profile_id}", response_model=StudentProfileOut)
def update_student_profile(profile_id: int, payload: StudentProfileUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id, StudentProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    updated_values = payload.model_dump(exclude_unset=True)
    for field_name, value in updated_values.items():
        setattr(profile, field_name, value)

    db.commit()
    db.refresh(profile)
    # Schedule re-indexing asynchronously on profile update.
    try:
        if not DISABLE_INDEXING:
            threading.Thread(target=_match_service().index_student_profile_embedding, args=(profile,), daemon=True).start()
    except Exception:
        pass
    return profile


@api_router.get("/profile/{profile_id}", response_model=StudentProfileOut)
def get_student_profile(profile_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id, StudentProfile.user_id == current_user.id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    return profile


@router.post("/recommend", response_model=UniversityRecommendationResponse)
@api_router.post("/recommend", response_model=UniversityRecommendationResponse)
async def recommend_universities(payload: UniversityRecommendationRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    try:
        from core.rag_service import generate_match_analysis_async
    except Exception as exc:
        raise HTTPException(status_code=503, detail="University recommendation dependencies are unavailable") from exc

    student_profile = db.query(StudentProfile).filter(StudentProfile.id == payload.student_profile_id, StudentProfile.user_id == current_user.id).first()
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    intended_major = (payload.intended_major or student_profile.intended_major or "").strip()
    if not intended_major:
        raise HTTPException(status_code=422, detail="intended_major is required")

    major_matches = (
        db.query(Program)
        .join(University, University.id == Program.university_id)
        .filter(func.lower(Program.name).like(f"%{intended_major.lower()}%"))
        .order_by(University.country.asc(), University.name.asc(), Program.name.asc())
        .all()
    )

    matching_programs = major_matches
    if not matching_programs and student_profile.degree_level:
        matching_programs = (
            db.query(Program)
            .join(University, University.id == Program.university_id)
            .filter(func.lower(Program.degree_level).like(f"%{student_profile.degree_level.lower()}%"))
            .order_by(University.country.asc(), University.name.asc(), Program.name.asc())
            .all()
        )

    recommendations = []
    now = datetime.utcnow()
    expires_at = now + timedelta(days=MATCH_CACHE_TTL_DAYS)

    if DISABLE_INDEXING:
        for program in matching_programs[:10]:
            university = db.query(University).filter(University.id == program.university_id).first()
            if not university:
                continue
            ranking_value = university.ranking_global if university.ranking_global is not None else (_safe_int(university.ranking) or 9999)
            tuition_value = int(program.estimated_tuition_fees or 0)
            fit_score = max(50, min(98, 98 - min(30, ranking_value // 5) - min(18, tuition_value // 2000)))
            recommendations.append(
                UniversityRecommendationItem(
                    university=UniversityOut.model_validate(university),
                    program=ProgramOut.model_validate(program),
                    match_score=int(fit_score),
                    explanation="Quick dev fallback recommendation while indexing is disabled.",
                    cached=False,
                    cache_expires_at=None,
                )
            )

        return UniversityRecommendationResponse(
            student_profile=StudentProfileOut.model_validate(student_profile),
            recommendations=recommendations,
        )

    for program in matching_programs:
        university = db.query(University).filter(University.id == program.university_id).first()
        if not university:
            continue

        cached = _cache_lookup(db, current_user.id, student_profile.id, program.id, intended_major)
        if cached:
            recommendations.append(
                UniversityRecommendationItem(
                    university=UniversityOut.model_validate(university),
                    program=ProgramOut.model_validate(program),
                    match_score=int(cached.match_score),
                    explanation=cached.explanation,
                    cached=True,
                    cache_expires_at=cached.expires_at,
                )
            )
            continue

        match_score, explanation, source_ids, _retrieved = await generate_match_analysis_async(
            _profile_to_dict(student_profile),
            _program_to_dict(program),
            _university_to_dict(university),
            top_k=5,
            metadata_filter={"doc_type": "university_program"},
        )

        cache_row = UniversityMatchCache(
            user_id=current_user.id,
            student_profile_id=student_profile.id,
            program_id=program.id,
            intended_major=intended_major,
            match_score=int(match_score),
            explanation=explanation,
            source_ids=source_ids,
            cached_at=now,
            expires_at=expires_at,
        )
        db.add(cache_row)
        db.commit()
        db.refresh(cache_row)

        recommendations.append(
            UniversityRecommendationItem(
                university=UniversityOut.model_validate(university),
                program=ProgramOut.model_validate(program),
                match_score=int(match_score),
                explanation=explanation,
                cached=False,
                cache_expires_at=cache_row.expires_at,
            )
        )

    return UniversityRecommendationResponse(
        student_profile=StudentProfileOut.model_validate(student_profile),
        recommendations=recommendations,
    )


def _match_row_to_out(match_payload: Dict[str, Any], db: Session | None = None) -> StudentProgramMatchOut:
    # If payload is already a dict that contains the full 'id', use it directly
    fields = StudentProgramMatchOut.model_fields.keys()
    if isinstance(match_payload, dict) and "id" in match_payload:
        payload = {key: match_payload[key] for key in fields if key in match_payload}
        return StudentProgramMatchOut.model_validate(payload)

    # If DB session available and we have student_id/program_id, try to load canonical row
    if db is not None and isinstance(match_payload, dict) and match_payload.get("student_id") and match_payload.get("program_id"):
        try:
            row = db.query(StudentProgramMatch).filter(
                StudentProgramMatch.student_id == int(match_payload.get("student_id")),
                StudentProgramMatch.program_id == int(match_payload.get("program_id")),
            ).first()
            if row is not None:
                return StudentProgramMatchOut.model_validate(row)
        except Exception:
            pass

    # Fallback: build a payload from whatever keys exist and ensure 'id' exists
        payload = {
            "id": int(getattr(match_payload, "id", 0) or 0),
            "student_id": match_payload.get("student_id"),
            "program_id": match_payload.get("program_id"),
            "match_score": match_payload.get("match_score"),
            "academic_fit": match_payload.get("academic_fit"),
            "budget_fit": match_payload.get("budget_fit"),
            "location_fit": match_payload.get("location_fit"),
            "missing_requirements": match_payload.get("missing_requirements"),
            "strengths": match_payload.get("strengths"),
            "recommendations": match_payload.get("recommendations"),
            "summary": match_payload.get("summary"),
            "vector_similarity": match_payload.get("vector_similarity"),
            "cached": match_payload.get("cached", False),
        }
    return StudentProgramMatchOut.model_validate(payload)


@api_router.post("/match/recommend", response_model=UniversityMatchRecommendResponse)
def match_recommend(payload: UniversityMatchRecommendRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student_profile = db.query(StudentProfile).filter(StudentProfile.id == payload.student_profile_id, StudentProfile.user_id == current_user.id).first()
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    if os.getenv("TESTING_MODE", "false").lower() in {"1", "true", "yes", "on"}:
        return UniversityMatchRecommendResponse(
            student_profile=StudentProfileOut.model_validate(student_profile),
            results=[],
        )

    try:
        candidates = _match_service().retrieve_similar_programs(student_profile.id, current_user.id, limit=max(payload.limit * 3, payload.limit), db=db)
    except Exception as exc:
        logger.exception("University recommendation candidate retrieval failed for student_profile_id=%s", student_profile.id)
        return UniversityMatchRecommendResponse(
            student_profile=StudentProfileOut.model_validate(student_profile),
            results=[],
        )

    allowed_countries = {country.strip().lower() for country in payload.filter_countries if country.strip()}
    results: List[Dict[str, Any]] = []
    for candidate in candidates:
        university_payload = candidate["university"]
        program_payload = candidate["program"]
        if allowed_countries and (university_payload.get("country") or "").strip().lower() not in allowed_countries:
            continue
        if payload.filter_max_tuition is not None and int(program_payload.get("estimated_tuition_fees") or 0) > payload.filter_max_tuition:
            continue
        if payload.filter_scholarship_only and not (
            program_payload.get("scholarship_available")
            or db.query(Scholarship.id).filter(Scholarship.university_id == int(university_payload["id"])).first()
        ):
            continue

        try:
            match_payload = _match_service().get_match_for_program(student_profile.id, int(candidate["program_id"]), current_user.id, db)
        except Exception:
            logger.exception(
                "University recommendation scoring failed for student_profile_id=%s program_id=%s",
                student_profile.id,
                candidate.get("program_id"),
            )
            continue
        if int(match_payload.get("match_score", 0)) < payload.min_match_score:
            continue

        results.append(
            {
                "university": UniversityOut.model_validate(university_payload),
                "program": ProgramOut.model_validate(program_payload),
                "vector_similarity": int(candidate["vector_similarity"]),
                "match": match_payload,
            }
        )

    if payload.sort_by == "ranking":
        results.sort(key=lambda item: (item["university"].ranking_global is None, item["university"].ranking_global or 10**9, -item["match"]["match_score"]))
    elif payload.sort_by == "tuition":
        results.sort(key=lambda item: (item["program"].estimated_tuition_fees or 10**9, -item["match"]["match_score"]))
    elif payload.sort_by == "country":
        results.sort(key=lambda item: ((item["university"].country or "").lower(), -item["match"]["match_score"]))
    else:
        results.sort(key=lambda item: item["match"]["match_score"], reverse=True)

    response_items = [
        UniversityMatchProgramItem(
            university=item["university"],
            program=item["program"],
            vector_similarity=int(item["vector_similarity"]),
            match=_match_row_to_out(item["match"], db=db),
            cached=bool(item["match"].get("cached", False)),
        )
        for item in results[: payload.limit]
    ]

    return UniversityMatchRecommendResponse(
        student_profile=StudentProfileOut.model_validate(student_profile),
        results=response_items,
    )


def _match_detail_response(student_profile: StudentProfile, match_payload: Dict[str, Any], db: Session) -> UniversityMatchDetailResponse:
    match = _match_row_to_out(match_payload, db=db)
    analysis = {
        "match_score": match.match_score,
        "academic_fit": match.academic_fit,
        "budget_fit": match.budget_fit,
        "location_fit": match.location_fit,
        "missing_requirements": match.missing_requirements,
        "strengths": match.strengths,
        "recommendations": match.recommendations,
        "summary": match.summary,
        "vector_similarity": match_payload.get("vector_similarity"),
        "cached": match_payload.get("cached", False),
    }
    return UniversityMatchDetailResponse(
        student_profile=StudentProfileOut.model_validate(student_profile),
        university=UniversityOut.model_validate(match_payload["university"]),
        program=ProgramOut.model_validate(match_payload["program"]),
        match=match,
        analysis=analysis,
    )


@api_router.get("/match/program/{program_id}", response_model=UniversityMatchDetailResponse)
def match_program(program_id: int, student_profile_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student_profile = db.query(StudentProfile).filter(StudentProfile.id == student_profile_id, StudentProfile.user_id == current_user.id).first()
    if not student_profile:
        raise HTTPException(status_code=404, detail="Student profile not found")

    try:
        match_payload = _match_service().get_match_for_program(student_profile_id, program_id, current_user.id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _match_detail_response(student_profile, match_payload, db=db)


@api_router.get("/match/explain", response_model=UniversityMatchDetailResponse)
def match_explain(student_profile_id: int, program_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return match_program(program_id=program_id, student_profile_id=student_profile_id, current_user=current_user, db=db)


def _saved_program_out(saved_program: SavedProgram, program: Program, university: University) -> SavedProgramOut:
    return SavedProgramOut.model_validate(
        {
            "id": saved_program.id,
            "student_id": saved_program.student_id,
            "program_id": saved_program.program_id,
            "saved_at": saved_program.saved_at,
            "program": ProgramOut.model_validate(program),
            "university": UniversityOut.model_validate(university),
        }
    )


def _study_application_out(application: StudyApplication, program: Program, university: University) -> StudyApplicationOut:
    return StudyApplicationOut.model_validate(
        {
            "id": application.id,
            "student_id": application.student_id,
            "program_id": application.program_id,
            "status": application.status,
            "notes": application.notes,
            "applied_at": application.applied_at,
            "deadline": application.deadline,
            "created_at": application.created_at,
            "updated_at": application.updated_at,
            "program": ProgramOut.model_validate(program),
            "university": UniversityOut.model_validate(university),
        }
    )


@api_router.post("/save")
def save_program(payload: StudentSaveRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(StudentProfile).filter(StudentProfile.id == payload.student_id, StudentProfile.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    program_row = db.query(Program).filter(Program.id == payload.program_id).first()
    if not program_row:
        raise HTTPException(status_code=404, detail="Program not found")

    existing = (
        db.query(SavedProgram)
        .filter(SavedProgram.user_id == current_user.id, SavedProgram.student_id == payload.student_id, SavedProgram.program_id == payload.program_id)
        .first()
    )
    if existing:
        return {"status": "success", "saved": True, "id": existing.id}

    saved = SavedProgram(user_id=current_user.id, student_id=payload.student_id, program_id=payload.program_id)
    db.add(saved)
    db.commit()
    db.refresh(saved)
    return {"status": "success", "saved": True, "id": saved.id}


@api_router.get("/saved/{student_id}")
def list_saved_programs(student_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(SavedProgram, Program, University)
        .join(Program, Program.id == SavedProgram.program_id)
        .join(University, University.id == Program.university_id)
        .filter(SavedProgram.user_id == current_user.id, SavedProgram.student_id == student_id)
        .order_by(SavedProgram.saved_at.desc())
        .all()
    )
    return [
        _saved_program_out(saved_program, program, university).model_dump()
        for saved_program, program, university in rows
    ]


@api_router.post("/apply")
def apply_program(payload: StudentApplyRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(StudentProfile).filter(StudentProfile.id == payload.student_id, StudentProfile.user_id == current_user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    program_row = db.query(Program).filter(Program.id == payload.program_id).first()
    if not program_row:
        raise HTTPException(status_code=404, detail="Program not found")

    application = StudyApplication(
        user_id=current_user.id,
        student_id=payload.student_id,
        program_id=payload.program_id,
        status="applied",
        notes=payload.notes,
        applied_at=datetime.utcnow(),
        deadline=program_row.application_deadline,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return {"status": "success", "id": application.id, "application_status": application.status}


@api_router.put("/applications/{application_id}")
def update_study_application(application_id: int, payload: StudyApplicationUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    application = db.query(StudyApplication).filter(StudyApplication.id == application_id, StudyApplication.user_id == current_user.id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = payload.status
    if payload.notes is not None:
        application.notes = payload.notes
    db.commit()
    db.refresh(application)
    return {"status": "success", "id": application.id, "application_status": application.status}


@api_router.get("/applications/{student_id}")
def list_study_applications(student_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (
        db.query(StudyApplication, Program, University)
        .join(Program, Program.id == StudyApplication.program_id)
        .join(University, University.id == Program.university_id)
        .filter(StudyApplication.user_id == current_user.id, StudyApplication.student_id == student_id)
        .order_by(StudyApplication.updated_at.desc())
        .all()
    )
    return [
        _study_application_out(application, program, university).model_dump()
        for application, program, university in rows
    ]