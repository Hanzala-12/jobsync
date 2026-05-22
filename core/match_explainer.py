from __future__ import annotations

import time
from typing import List, Dict, Tuple

from core.skill_extractor import normalize_skill, extract_skills

# Simple in-memory cache for explanations
_CACHE: Dict[Tuple[int, int], Tuple[float, Dict]] = {}
_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days


def _now() -> float:
    return time.time()


def calculate_skill_match(profile_skills: List[str], job_skills: List[str]) -> Tuple[List[str], List[str]]:
    p = {normalize_skill(s).lower() for s in (profile_skills or []) if s}
    j = {normalize_skill(s).lower() for s in (job_skills or []) if s}
    matched = sorted([s.title() for s in (p & j)])
    missing = sorted([s.title() for s in (j - p)])
    return matched, missing


def calculate_experience_match(profile_years: int | None, job_min: int | None, job_max: int | None) -> str:
    try:
        if profile_years is None:
            return "Experience not provided in profile"
        if job_min is None and job_max is None:
            return "No explicit experience requirement"
        if job_min is None:
            job_min = 0
        if job_max is None:
            job_max = job_min

        if job_min <= profile_years <= job_max:
            return f"Your {profile_years} years of experience aligns with requirement of {job_min}-{job_max} years"
        if profile_years < job_min:
            return f"You have {profile_years} years; role expects at least {job_min} years"
        return f"You have {profile_years} years which exceeds the stated range of {job_min}-{job_max} years"
    except Exception:
        return "Experience fit could not be determined"


def generate_recommendations(missing_skills: List[str]) -> List[str]:
    recs = []
    for skill in (missing_skills or [])[:10]:
        s = normalize_skill(skill)
        recs.append(f"Learn {s} via free online resources and add a short project demonstrating it.")
    if not recs:
        recs.append("Highlight transferable projects and quantify impact in your bullets.")
    return recs


def explain_match_for(job: Dict, profile: Dict) -> Dict:
    """Compute an explainable match payload for a job and profile dicts.

    Expects job to contain 'id', 'description', optionally 'experience_required' text.
    Profile should contain 'id', 'resume_text', optionally 'experience_years' and 'degree_level'.
    """
    job_id = int(job.get("id") or 0)
    profile_id = int(profile.get("id") or 0)

    key = (profile_id, job_id)
    cached = _CACHE.get(key)
    if cached and (_now() - cached[0]) < _TTL_SECONDS:
        return cached[1]

    job_text = job.get("description", "") or ""
    profile_text = profile.get("resume_text", "") or ""

    job_skills = job.get("job_skills") or extract_skills(job_text, limit=50)
    profile_skills = profile.get("profile_skills") or extract_skills(profile_text, limit=50)

    matched, missing = calculate_skill_match(profile_skills, job_skills)

    # naive experience extraction from job.experience_required like '2-4 years'
    job_min = None
    job_max = None
    exp_text = str(job.get("experience_required") or "")
    import re as _re
    m = _re.search(r"(\d+)\s*-\s*(\d+)", exp_text)
    if m:
        job_min = int(m.group(1))
        job_max = int(m.group(2))
    else:
        m2 = _re.search(r"(\d+)\s*\+?\s*years", exp_text)
        if m2:
            job_min = int(m2.group(1))
            job_max = None

    profile_years = profile.get("experience_years") or None
    experience_fit = calculate_experience_match(profile_years, job_min, job_max)

    education_fit = "Not evaluated"
    if profile.get("degree_level") and job.get("degree_level"):
        if profile.get("degree_level", "").lower() in str(job.get("degree_level", "")).lower():
            education_fit = "Degree level appears to match requirement"
        else:
            education_fit = "Degree level may not match requirement"

    recommendations = generate_recommendations(missing)

    payload = {
        "match_score": int(min(100, max(0, (len(matched) * 10)))),
        "matching_skills": matched,
        "missing_skills": missing,
        "experience_fit": experience_fit,
        "education_fit": education_fit,
        "recommendations": recommendations,
    }

    _CACHE[key] = (_now(), payload)
    return payload
