from __future__ import annotations

import json
import math
import re
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from backend.models import Program, StudentProfile, StudentProgramMatch, University
from core.llm_provider import LLMProvider
from core.rag_service import DEFAULT_COLLECTION_NAME, RetrievedChunk, get_chroma_collection, get_embedding_model


MATCH_CACHE_TTL_DAYS = 7
PROFILE_DOC_TYPE = "student_profile"
PROGRAM_DOC_TYPE = "university_program"


def _now() -> datetime:
    return datetime.utcnow()


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except Exception:
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _list_text(values: Iterable[Any]) -> str:
    cleaned = [str(value).strip() for value in values if str(value).strip()]
    return ", ".join(cleaned) if cleaned else "Any"


def _student_profile_document(profile: StudentProfile) -> str:
    parts = [
        "Student Profile:",
        f"GPA: {profile.gpa}",
        f"GRE: {profile.gre_score if profile.gre_score is not None else 'N/A'}",
        f"TOEFL: {profile.toefl_score if profile.toefl_score is not None else 'N/A'}",
        f"IELTS: {profile.ielts_score if profile.ielts_score is not None else 'N/A'}",
        f"Budget: ${profile.budget_per_year} per year",
        f"Preferred Countries: {_list_text(profile.preferred_countries or [])}",
        f"Intended Major: {profile.intended_major}",
        f"Degree Level: {profile.degree_level}",
        f"Academic Background: {profile.academic_background or profile.intended_major or 'Not provided'}",
    ]
    return "\n\n".join(parts)


def _program_document(program: Program, university: University) -> str:
    tuition = program.estimated_tuition_fees or 0
    living_cost = program.living_cost_estimate or 0
    total_cost = tuition + living_cost
    ranking = program.ranking_global or university.ranking_global or university.ranking or "N/A"
    lines = [
        f"Program: {program.name}",
        f"University: {university.name}",
        f"Country: {university.country}",
        f"Global Ranking: {ranking}",
        f"Tuition Fees: ${tuition:,} per year" if tuition else "Tuition Fees: N/A",
        f"Living Costs: ${living_cost:,} per year" if living_cost else "Living Costs: N/A",
        f"Total Estimated Cost: ${total_cost:,} per year" if total_cost else "Total Estimated Cost: N/A",
        f"Minimum GPA Required: {program.min_gpa if program.min_gpa is not None else 'N/A'}",
        f"IELTS Required: {program.min_ielts if program.min_ielts is not None else 'N/A'}",
        f"TOEFL Required: {program.min_toefl if program.min_toefl is not None else 'N/A'}",
        f"Intake: {program.semester_intake or 'N/A'}",
        f"Scholarship Available: {'Yes' if program.scholarship_available else 'No'}",
        f"Program URL: {program.program_url or university.website or 'N/A'}",
    ]
    return "\n".join(lines)


def _program_payload(program: Program, university: University) -> Dict[str, Any]:
    total_cost = (program.estimated_tuition_fees or 0) + (program.living_cost_estimate or 0)
    return {
        "id": program.id,
        "university_id": university.id,
        "name": program.name,
        "degree_level": program.degree_level,
        "duration_years": program.duration_years,
        "estimated_tuition_fees": program.estimated_tuition_fees,
        "currency": program.currency,
        "min_gpa": program.min_gpa,
        "ranking_global": program.ranking_global or university.ranking_global,
        "ranking_national": program.ranking_national,
        "min_ielts": program.min_ielts,
        "min_toefl": program.min_toefl,
        "application_deadline": program.application_deadline,
        "semester_intake": program.semester_intake,
        "living_cost_estimate": program.living_cost_estimate,
        "scholarship_available": bool(program.scholarship_available),
        "program_url": program.program_url or university.website,
        "total_cost": total_cost,
    }


def _university_payload(university: University) -> Dict[str, Any]:
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


def _cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    numerator = 0.0
    left_norm = 0.0
    right_norm = 0.0
    for left_value, right_value in zip(left, right):
        numerator += left_value * right_value
        left_norm += left_value * left_value
        right_norm += right_value * right_value
    if not left_norm or not right_norm:
        return 0.0
    return numerator / math.sqrt(left_norm * right_norm)


def _embedding(text: str) -> List[float]:
    model = get_embedding_model()
    embedding = model.encode([text], convert_to_numpy=True)[0].tolist()
    return [float(value) for value in embedding]


def _get_collection():
    return get_chroma_collection(collection_name=DEFAULT_COLLECTION_NAME)


def index_student_profile_embedding(profile: StudentProfile, *, delete_existing: bool = True) -> str:
    collection = _get_collection()
    if delete_existing:
        try:
            collection.delete(where={"doc_type": PROFILE_DOC_TYPE, "student_id": profile.id})
        except Exception:
            pass

    profile_version = _now().isoformat()
    document = _student_profile_document(profile)
    collection.add(
        ids=[f"student_profile_{profile.id}_{profile_version}"],
        documents=[document],
        metadatas=[
            {
                "doc_type": PROFILE_DOC_TYPE,
                "student_id": profile.id,
                "profile_version": profile_version,
            }
        ],
        embeddings=[_embedding(document)],
    )
    return profile_version


def index_program_embedding(program: Program, university: University, *, delete_existing: bool = True) -> str:
    collection = _get_collection()
    if delete_existing:
        try:
            collection.delete(where={"doc_type": PROGRAM_DOC_TYPE, "program_id": program.id})
        except Exception:
            pass

    document = _program_document(program, university)
    document_version = _now().isoformat()
    collection.add(
        ids=[f"program_{program.id}_{document_version}"],
        documents=[document],
        metadatas=[
            {
                "doc_type": PROGRAM_DOC_TYPE,
                "program_id": program.id,
                "university_id": university.id,
                "university_name": university.name,
                "country": university.country,
                "ranking": university.ranking_global or university.ranking,
                "tuition": program.estimated_tuition_fees,
                "living_cost": program.living_cost_estimate,
                "total_cost": (program.estimated_tuition_fees or 0) + (program.living_cost_estimate or 0),
            }
        ],
        embeddings=[_embedding(document)],
    )
    return document_version


def index_programs_to_vector_db(db: Session, *, limit: Optional[int] = None, country: Optional[str] = None) -> int:
    query = db.query(Program, University).join(University, University.id == Program.university_id).order_by(University.name.asc(), Program.name.asc())
    if country:
        query = query.filter(University.country.ilike(country.strip()))
    rows = query.all()
    if limit is not None:
        rows = rows[: max(0, limit)]

    indexed = 0
    for program, university in rows:
        index_program_embedding(program, university)
        indexed += 1
    return indexed


def _student_similarity_score(student_profile: StudentProfile, program: Program, university: University) -> int:
    student_document = _student_profile_document(student_profile)
    program_document = _program_document(program, university)
    student_embedding = _embedding(student_document)
    program_embedding = _embedding(program_document)
    similarity = (_cosine_similarity(student_embedding, program_embedding) + 1.0) / 2.0
    score = int(round(max(0.0, min(1.0, similarity)) * 100))

    budget = student_profile.budget_per_year or 0
    total_cost = (program.estimated_tuition_fees or 0) + (program.living_cost_estimate or 0)
    if budget and total_cost and budget < total_cost:
        gap_ratio = (total_cost - budget) / max(total_cost, 1)
        penalty = min(35, max(8, int(round(gap_ratio * 50))))
        score = max(0, score - penalty)
    return score


def retrieve_similar_programs(student_id: int, limit: int = 20, db: Optional[Session] = None) -> List[Dict[str, Any]]:
    if db is None:
        raise ValueError("db session is required")

    student_profile = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student_profile:
        raise ValueError("Student profile not found")

    student_document = _student_profile_document(student_profile)
    query_embedding = _embedding(student_document)
    collection = _get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=max(1, limit * 3),
        where={"doc_type": PROGRAM_DOC_TYPE},
    )

    ids = (results.get("ids") or [[]])[0]
    metadatas = (results.get("metadatas") or [[]])[0]
    distances = (results.get("distances") or [[]])[0]

    candidate_program_ids = []
    for metadata in metadatas:
        try:
            program_id = int(metadata.get("program_id"))
        except Exception:
            continue
        if program_id not in candidate_program_ids:
            candidate_program_ids.append(program_id)

    if not candidate_program_ids:
        programs = (
            db.query(Program, University)
            .join(University, University.id == Program.university_id)
            .order_by(University.ranking_global.asc().nullslast(), University.name.asc())
            .limit(limit)
            .all()
        )
        candidate_program_ids = [program.id for program, _university in programs]

    program_rows = (
        db.query(Program, University)
        .join(University, University.id == Program.university_id)
        .filter(Program.id.in_(candidate_program_ids))
        .all()
    )
    program_map = {program.id: (program, university) for program, university in program_rows}

    ranked: List[Dict[str, Any]] = []
    for rank_index, metadata in enumerate(metadatas):
        try:
            program_id = int(metadata.get("program_id"))
        except Exception:
            continue
        if program_id not in program_map:
            continue
        program, university = program_map[program_id]
        base_distance = _safe_float(distances[rank_index] if rank_index < len(distances) else 0.0)
        vector_similarity = int(round(max(0.0, min(1.0, 1.0 - base_distance)) * 100))
        if vector_similarity <= 0:
            vector_similarity = _student_similarity_score(student_profile, program, university)
        if student_profile.budget_per_year and (program.estimated_tuition_fees or 0) + (program.living_cost_estimate or 0) > student_profile.budget_per_year:
            total_cost = (program.estimated_tuition_fees or 0) + (program.living_cost_estimate or 0)
            gap = total_cost - student_profile.budget_per_year
            penalty = min(30, max(5, int(round((gap / max(total_cost, 1)) * 40))))
            vector_similarity = max(0, vector_similarity - penalty)

        ranked.append(
            {
                "program_id": program.id,
                "university_id": university.id,
                "university": _university_payload(university),
                "program": _program_payload(program, university),
                "vector_similarity": vector_similarity,
                "distance": base_distance,
            }
        )

    ranked.sort(key=lambda item: item["vector_similarity"], reverse=True)
    return ranked[:limit]


def _heuristic_match_result(student_profile: StudentProfile, program: Program, university: University, vector_similarity: int) -> Dict[str, Any]:
    preferred_countries = {str(item).strip().lower() for item in (student_profile.preferred_countries or []) if str(item).strip()}
    country = (university.country or "").strip().lower()
    academic_fit = 60
    budget_fit = 60
    location_fit = 50
    missing_requirements: List[str] = []
    strengths: List[str] = []
    recommendations: List[str] = []

    if program.min_gpa is not None:
        if student_profile.gpa >= program.min_gpa:
            academic_fit += 25
            strengths.append("GPA meets the minimum requirement")
        else:
            deficit = program.min_gpa - student_profile.gpa
            academic_fit -= min(35, max(10, int(round(deficit * 20))))
            missing_requirements.append(f"GPA below minimum {program.min_gpa}")
            recommendations.append("Raise GPA or strengthen the rest of the application")

    if program.min_toefl is not None:
        if student_profile.toefl_score is not None and student_profile.toefl_score >= program.min_toefl:
            academic_fit += 10
            strengths.append("TOEFL score meets the requirement")
        else:
            missing_requirements.append(f"TOEFL below minimum {program.min_toefl}")

    if program.min_ielts is not None:
        if student_profile.ielts_score is not None and student_profile.ielts_score >= program.min_ielts:
            academic_fit += 10
            strengths.append("IELTS score meets the requirement")
        else:
            missing_requirements.append(f"IELTS minimum is {program.min_ielts}")

    total_cost = (program.estimated_tuition_fees or 0) + (program.living_cost_estimate or 0)
    if student_profile.budget_per_year >= total_cost and total_cost > 0:
        budget_fit += 30
        strengths.append("Budget covers estimated annual cost")
    elif total_cost > 0:
        gap = total_cost - student_profile.budget_per_year
        budget_fit -= min(40, max(10, int(round((gap / max(total_cost, 1)) * 60))))
        missing_requirements.append("Budget may not cover tuition plus living cost")
        recommendations.append("Look for scholarships or lower-cost options")

    if country in preferred_countries:
        location_fit += 30
        strengths.append("Program is in a preferred country")
    elif preferred_countries:
        location_fit -= 10

    if student_profile.degree_level.lower() == program.degree_level.lower():
        academic_fit += 5
    else:
        missing_requirements.append(f"Program degree level is {program.degree_level}")

    match_score = int(round((academic_fit * 0.5) + (budget_fit * 0.3) + (location_fit * 0.2)))
    match_score = max(0, min(100, int(round((match_score * 0.7) + (vector_similarity * 0.3)))))
    academic_fit = max(0, min(100, academic_fit))
    budget_fit = max(0, min(100, budget_fit))
    location_fit = max(0, min(100, location_fit))

    if not strengths:
        strengths.append("Program appears broadly aligned with the student profile")
    if not recommendations:
        recommendations.append("Prepare a focused statement of purpose and recommendation letters")

    return {
        "match_score": match_score,
        "academic_fit": academic_fit,
        "budget_fit": budget_fit,
        "location_fit": location_fit,
        "missing_requirements": list(dict.fromkeys(missing_requirements)),
        "strengths": list(dict.fromkeys(strengths)),
        "recommendations": list(dict.fromkeys(recommendations)),
        "summary": f"This program is a {match_score}% fit based on the current profile, budget, and location preferences.",
    }


def _match_prompt(student_profile: StudentProfile, program: Program, university: University, vector_similarity: int) -> str:
    total_cost = (program.estimated_tuition_fees or 0) + (program.living_cost_estimate or 0)
    preferred_countries = _list_text(student_profile.preferred_countries or [])
    return f"""You are an expert university admissions counselor. Based on the student profile and program requirements below, calculate a match score (0-100) and provide a structured analysis.

STUDENT PROFILE:

GPA: {student_profile.gpa}

GRE: {student_profile.gre_score if student_profile.gre_score is not None else 'N/A'}, TOEFL: {student_profile.toefl_score if student_profile.toefl_score is not None else 'N/A'}, IELTS: {student_profile.ielts_score if student_profile.ielts_score is not None else 'N/A'}

Budget (annual): ${student_profile.budget_per_year}

Preferred countries: {preferred_countries}

Intended major: {student_profile.intended_major}

Degree level: {student_profile.degree_level}

Academic background: {student_profile.academic_background or 'Not provided'}

PROGRAM DETAILS:

University: {university.name} ({university.country})

Program: {program.name}

Global Ranking: {program.ranking_global or university.ranking_global or university.ranking or 'N/A'}

Minimum GPA: {program.min_gpa if program.min_gpa is not None else 'N/A'}

IELTS/TOEFL: {program.min_ielts if program.min_ielts is not None else 'N/A'}/{program.min_toefl if program.min_toefl is not None else 'N/A'}

Total Annual Cost (tuition + living): ${total_cost}

Scholarship available: {'Yes' if program.scholarship_available else 'No'}

Vector similarity score: {vector_similarity}

OUTPUT IN JSON FORMAT ONLY (no extra text):
{{
"match_score": integer (0-100),
"academic_fit": integer (0-100),
"budget_fit": integer (0-100),
"location_fit": integer (0-100),
"missing_requirements": ["list of missing items"],
"strengths": ["list of strengths"],
"recommendations": ["list of suggestions to improve chances"],
"summary": "one sentence summary"
}}
"""


def _parse_json_payload(content: str) -> Dict[str, Any]:
    raw = (content or "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            parsed = json.loads(raw[start : end + 1])
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass
    return {}


def calculate_match_score(student_profile: StudentProfile, program: Program, university: University, *, vector_similarity: int = 0) -> Dict[str, Any]:
    prompt = _match_prompt(student_profile, program, university, vector_similarity)
    system_prompt = "You evaluate university admissions fit and always return strict JSON with the requested keys only."

    analysis: Dict[str, Any] = {}
    try:
        provider = LLMProvider()
        response = provider.ask(system_prompt, prompt, temperature=0.2)
        analysis = _parse_json_payload(response)
    except Exception:
        analysis = {}

    fallback = _heuristic_match_result(student_profile, program, university, vector_similarity)
    result = {
        "match_score": _safe_int(analysis.get("match_score"), fallback["match_score"]),
        "academic_fit": _safe_int(analysis.get("academic_fit"), fallback["academic_fit"]),
        "budget_fit": _safe_int(analysis.get("budget_fit"), fallback["budget_fit"]),
        "location_fit": _safe_int(analysis.get("location_fit"), fallback["location_fit"]),
        "missing_requirements": analysis.get("missing_requirements") if isinstance(analysis.get("missing_requirements"), list) else fallback["missing_requirements"],
        "strengths": analysis.get("strengths") if isinstance(analysis.get("strengths"), list) else fallback["strengths"],
        "recommendations": analysis.get("recommendations") if isinstance(analysis.get("recommendations"), list) else fallback["recommendations"],
        "summary": str(analysis.get("summary") or fallback["summary"])[:500],
    }

    if not result["match_score"]:
        result["match_score"] = fallback["match_score"] or vector_similarity
    result["match_score"] = max(0, min(100, int(result["match_score"])))
    result["academic_fit"] = max(0, min(100, int(result["academic_fit"])))
    result["budget_fit"] = max(0, min(100, int(result["budget_fit"])))
    result["location_fit"] = max(0, min(100, int(result["location_fit"])))
    return result


def _serialize_match_row(row: StudentProgramMatch, student_profile: StudentProfile, program: Program, university: University, *, vector_similarity: int, cached: bool) -> Dict[str, Any]:
    return {
        "id": int(getattr(row, "id", 0) or 0),
        "student_id": row.student_id,
        "program_id": row.program_id,
        "match_score": row.match_score,
        "academic_fit": row.academic_fit,
        "budget_fit": row.budget_fit,
        "location_fit": row.location_fit,
        "missing_requirements": row.missing_requirements or [],
        "strengths": row.strengths or [],
        "recommendations": row.recommendations or [],
        "summary": row.summary,
        "computed_at": row.computed_at,
        "expires_at": row.expires_at,
        "cached": cached,
        "vector_similarity": vector_similarity,
        "student_profile": student_profile,
        "program": program,
        "university": university,
    }


def _find_cached_match(db: Session, student_id: int, program_id: int) -> Optional[StudentProgramMatch]:
    return (
        db.query(StudentProgramMatch)
        .filter(
            StudentProgramMatch.student_id == student_id,
            StudentProgramMatch.program_id == program_id,
            StudentProgramMatch.expires_at > _now(),
        )
        .first()
    )


def _upsert_match_row(db: Session, student_id: int, program_id: int, analysis: Dict[str, Any]) -> StudentProgramMatch:
    row = db.query(StudentProgramMatch).filter(StudentProgramMatch.student_id == student_id, StudentProgramMatch.program_id == program_id).first()
    expires_at = _now() + timedelta(days=MATCH_CACHE_TTL_DAYS)
    if row is None:
        row = StudentProgramMatch(student_id=student_id, program_id=program_id, expires_at=expires_at)
        db.add(row)

    row.match_score = int(analysis["match_score"])
    row.academic_fit = int(analysis["academic_fit"])
    row.budget_fit = int(analysis["budget_fit"])
    row.location_fit = int(analysis["location_fit"])
    row.missing_requirements = list(analysis.get("missing_requirements") or [])
    row.strengths = list(analysis.get("strengths") or [])
    row.recommendations = list(analysis.get("recommendations") or [])
    row.summary = str(analysis.get("summary") or "")[:500]
    row.computed_at = _now()
    row.expires_at = expires_at
    db.commit()
    db.refresh(row)
    return row


def get_match_for_program(student_id: int, program_id: int, db: Session) -> Dict[str, Any]:
    student_profile = db.query(StudentProfile).filter(StudentProfile.id == student_id).first()
    if not student_profile:
        raise ValueError("Student profile not found")

    program_row = db.query(Program, University).join(University, University.id == Program.university_id).filter(Program.id == program_id).first()
    if not program_row:
        raise ValueError("Program not found")
    program, university = program_row

    vector_similarity = _student_similarity_score(student_profile, program, university)
    cached = _find_cached_match(db, student_id, program_id)
    if cached:
        return _serialize_match_row(cached, student_profile, program, university, vector_similarity=vector_similarity, cached=True)

    analysis = calculate_match_score(student_profile, program, university, vector_similarity=vector_similarity)
    row = _upsert_match_row(db, student_id, program_id, analysis)
    return _serialize_match_row(row, student_profile, program, university, vector_similarity=vector_similarity, cached=False)


def refresh_match_cache(db: Session, *, profile_limit: Optional[int] = None, program_limit: int = 50) -> Dict[str, int]:
    profiles_query = db.query(StudentProfile).order_by(StudentProfile.created_at.desc())
    if profile_limit is not None:
        profiles = profiles_query.limit(profile_limit).all()
    else:
        profiles = profiles_query.all()

    refreshed_profiles = 0
    refreshed_matches = 0
    for profile in profiles:
        refreshed_profiles += 1
        candidates = retrieve_similar_programs(profile.id, limit=program_limit, db=db)
        for candidate in candidates:
            try:
                get_match_for_program(profile.id, int(candidate["program_id"]), db)
                refreshed_matches += 1
            except Exception:
                continue
    return {"profiles": refreshed_profiles, "matches": refreshed_matches}
