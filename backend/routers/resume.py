import json
import re
import tempfile
from typing import Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import ResumeVersion, UserPreference, UserProfile
from backend.schemas import (
    ResumeAnalysis,
    ResumeReanalysisRequest,
    ResumeRewriteRequest,
    ResumeRewriteResponse,
    ResumeVersionCreate,
    ResumeVersionOut,
    ResumeVersionUpdateUsedFor,
)
from backend.services.pdf_parser import extract_text_from_pdf
from core.llm_provider import LLMProvider

router = APIRouter(prefix="/resume", tags=["Resume"])
_STOP_WORDS = {
    "the", "and", "for", "with", "that", "this", "from", "your", "you", "are", "was",
    "were", "have", "has", "had", "will", "can", "not", "but", "our", "their", "they",
    "them", "its", "into", "about", "role", "job", "work", "using", "use", "used",
    "over", "under", "than", "then", "also", "while", "where", "when", "which",
}


def _extract_json(response: str, fallback: Dict):
    if not response:
        return fallback

    raw = response.strip()
    try:
        return json.loads(raw)
    except Exception:
        pass

    if "```" in raw:
        parts = [part.strip() for part in raw.split("```") if part.strip()]
        for part in parts:
            cleaned = part.replace("json", "", 1).strip()
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


def _normalize_rewritten_text(raw: str) -> str:
    text = (raw or "").strip()
    if not text:
        return ""
    if "```" in text:
        parts = [part.strip() for part in text.split("```") if part.strip()]
        if parts:
            candidate = parts[-1]
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            text = candidate.strip()
    return text


def _keyword_set(text: str) -> set[str]:
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{2,}", (text or "").lower())
    return {t for t in tokens if t not in _STOP_WORDS}


def _build_change_hints(original: str, rewritten: str, job_description: str) -> tuple[list[str], list[str], list[str]]:
    orig_kw = _keyword_set(original)
    rewrite_kw = _keyword_set(rewritten)
    job_kw = _keyword_set(job_description)

    keywords_added = sorted([k for k in (rewrite_kw - orig_kw) if k in job_kw])[:20]
    keywords_removed = sorted([k for k in (orig_kw - rewrite_kw) if k in job_kw])[:20]

    changes = []
    if rewritten.strip() != original.strip():
        changes.append("Resume wording and structure were updated to better match the target role.")
    if keywords_added:
        changes.append(f"Added {len(keywords_added)} role-relevant keywords from the job description.")
    if keywords_removed:
        changes.append(f"Removed or deprioritized {len(keywords_removed)} less-relevant terms.")
    if not changes:
        changes.append("Resume was reviewed, but no meaningful rewrite delta was detected.")

    return changes, keywords_added, keywords_removed


def _parse_profile_fields(text: str) -> dict[str, str]:
    fields = {
        "skills": "",
        "degree": "",
        "years_experience": "",
        "interests": "",
        "resume_text": "",
    }
    if not text:
        return fields

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    capture_resume = False
    resume_lines: list[str] = []
    for line in lines:
        lower = line.lower()
        if lower.startswith("skills:"):
            fields["skills"] = line.split(":", 1)[1].strip()
            continue
        if lower.startswith("degree:"):
            fields["degree"] = line.split(":", 1)[1].strip()
            continue
        if lower.startswith("years experience:"):
            fields["years_experience"] = line.split(":", 1)[1].strip()
            continue
        if lower.startswith("interests:"):
            fields["interests"] = line.split(":", 1)[1].strip()
            continue
        if lower.startswith("resume text:"):
            capture_resume = True
            maybe_text = line.split(":", 1)[1].strip()
            if maybe_text:
                resume_lines.append(maybe_text)
            continue
        if capture_resume:
            resume_lines.append(line)

    fields["resume_text"] = "\n".join(resume_lines).strip()
    return fields


def _top_job_keywords(job_description: str, limit: int = 10) -> list[str]:
    token_counts: dict[str, int] = {}
    for token in re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{2,}", (job_description or "").lower()):
        if token in _STOP_WORDS:
            continue
        token_counts[token] = token_counts.get(token, 0) + 1
    ranked = sorted(token_counts.items(), key=lambda item: (-item[1], item[0]))
    return [token for token, _ in ranked[:limit]]


def _is_placeholder_rewrite(text: str) -> bool:
    lowered = (text or "").strip().lower()
    if not lowered:
        return True
    placeholders = {
        "your rewritten resume",
        "rewritten resume",
        "updated resume",
        "optimized resume",
    }
    if lowered in placeholders:
        return True
    return lowered.startswith("your rewritten resume")


def _build_resume_fallback(source_resume_text: str, job_description: str, job_type: str) -> str:
    profile = _parse_profile_fields(source_resume_text)
    source_skills = [s.strip() for s in profile["skills"].split(",") if s.strip()]
    jd_keywords = _top_job_keywords(job_description, limit=8)

    merged_skills: list[str] = []
    seen_skills: set[str] = set()
    for skill in source_skills + jd_keywords:
        normalized = skill.strip()
        if not normalized:
            continue
        normalized_key = normalized.lower()
        if normalized_key in seen_skills:
            continue
        seen_skills.add(normalized_key)
        merged_skills.append(normalized)

    years = profile["years_experience"] or "0"
    degree = profile["degree"] or "Not specified"
    interests = profile["interests"] or "Continuous learning and technical growth"

    summary = (
        f"Early-career {job_type} candidate with {years} years of professional experience and a strong engineering "
        "foundation. Focused on structured problem solving, fast learning, and delivering reliable AI-enabled solutions."
    )

    strengths = [
        "Translate ambiguous requirements into practical implementation plans.",
        "Build and iterate clean, maintainable solutions with strong ownership.",
        "Collaborate effectively with cross-functional teams and communicate clearly.",
    ]
    if jd_keywords:
        strengths.append(f"Actively developing depth in: {', '.join(jd_keywords[:5])}.")

    return (
        "PROFESSIONAL SUMMARY\n"
        f"{summary}\n\n"
        "CORE SKILLS\n"
        f"- {', '.join(merged_skills[:12]) if merged_skills else 'Python, Problem Solving, Communication'}\n\n"
        "RELEVANT STRENGTHS\n"
        + "\n".join(f"- {item}" for item in strengths)
        + "\n\nEDUCATION\n"
        f"- {degree}\n\n"
        "EXPERIENCE SNAPSHOT\n"
        f"- Professional experience: {years} years\n"
        "- Prepared to contribute in AI/ML implementation, team collaboration, and iterative delivery.\n\n"
        "INTERESTS\n"
        f"- {interests}"
    )


def _unwrap_nested_rewrite_payload(rewritten: str) -> tuple[str, dict]:
    candidate = (rewritten or "").strip()
    if not candidate.startswith("{") or not candidate.endswith("}"):
        return rewritten, {}
    try:
        nested = json.loads(candidate)
    except Exception:
        return rewritten, {}
    if not isinstance(nested, dict):
        return rewritten, {}
    nested_rewritten = nested.get("rewritten")
    if isinstance(nested_rewritten, str) and nested_rewritten.strip():
        return nested_rewritten.strip(), nested
    return rewritten, {}


def _load_fallback_profile_text(db: Session) -> str:
    selected_id = None
    try:
        pref = db.query(UserPreference).order_by(UserPreference.updated_at.desc(), UserPreference.id.desc()).first()
        if pref and pref.selected_profile_id:
            selected_id = int(pref.selected_profile_id)
    except Exception:
        selected_id = None

    profile = None
    if selected_id:
        profile = db.query(UserProfile).filter(UserProfile.id == selected_id).first()
    if not profile:
        profile = db.query(UserProfile).order_by(UserProfile.created_at.desc()).first()
    return (profile.resume_text or "").strip() if profile else ""


@router.post("/analyze", response_model=ResumeAnalysis)
async def analyze_resume(file: UploadFile = File(...), db: Session = Depends(get_db)):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    text = extract_text_from_pdf(tmp_path)

    prompt = f"""Analyze this resume text for a tech job. Give:
1. ATS score (0-100)
2. Matched skills (list)
3. Missing important keywords (list)
4. Three specific improvement tips
Resume: {text[:3000]}
Respond in JSON format: {{"score": number, "matched_skills": ["..."], "keywords": ["..."], "tips": ["..."]}}"""

    llm = LLMProvider()
    parsed = _extract_json(
        llm.ask("You are a helpful career AI assistant.", prompt),
        {"score": 50, "matched_skills": [], "keywords": [], "tips": ["Add more role-specific keywords."]},
    )

    score = float(parsed.get("score", 50))
    matched_skills = parsed.get("matched_skills", []) or []
    keywords = parsed.get("keywords", []) or []
    tips = parsed.get("tips", []) or []

    profile = db.query(UserProfile).first()
    if not profile:
        profile = UserProfile()
        db.add(profile)

    profile.resume_text = text
    profile.skills = ", ".join(keywords) if keywords else ""
    profile.latest_ats_score = score
    db.commit()

    return ResumeAnalysis(
        ats_score=score,
        matched_skills=matched_skills,
        missing_keywords=keywords,
        tips=tips,
        resume_text=text,
    )


@router.post("/reanalyze", response_model=ResumeAnalysis)
def reanalyze_resume(req: ResumeReanalysisRequest, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).first()
    if not profile or not profile.resume_text:
        raise HTTPException(status_code=400, detail="Upload a resume first")

    prompt = f"""Compare this resume to the job description and return JSON only.

Resume:
{profile.resume_text[:3000]}

Job Description:
{req.job_description[:3000]}

Return exactly this JSON schema:
{{
  "score": number,
  "matched_skills": ["skill1", "skill2"],
  "missing_keywords": ["skill3", "skill4"],
  "tips": ["tip1", "tip2", "tip3"]
}}"""

    llm = LLMProvider()
    parsed = _extract_json(
        llm.ask("You are a strict ATS resume analyzer.", prompt),
        {
            "score": 50,
            "matched_skills": [],
            "missing_keywords": ["Could not parse"],
            "tips": ["Try re-running the analysis against the job description."],
        },
    )

    score = float(parsed.get("score", 50))
    matched_skills = parsed.get("matched_skills", []) or []
    missing_keywords = parsed.get("missing_keywords", []) or []
    tips = parsed.get("tips", []) or []

    profile.latest_ats_score = score
    profile.skills = ", ".join(matched_skills) if matched_skills else profile.skills
    db.commit()

    return ResumeAnalysis(
        ats_score=score,
        matched_skills=matched_skills,
        missing_keywords=missing_keywords,
        tips=tips,
        resume_text=profile.resume_text,
    )


@router.post("/rewrite", response_model=ResumeRewriteResponse)
def rewrite_resume(req: ResumeRewriteRequest, db: Session = Depends(get_db)):
    llm = LLMProvider()

    source_resume_text = (req.resume_text or "").strip()
    if not source_resume_text:
        source_resume_text = _load_fallback_profile_text(db)
    if not source_resume_text:
        raise HTTPException(status_code=400, detail="No resume text found. Paste resume text or upload/select a profile first.")

    prompt = f"""You are an expert resume writer. Rewrite this resume to match the job description.
Rules:
- Never invent experience or education
- Reorder bullets to match job priorities
- Replace generic words with job keywords
- Strengthen bullets with action verbs
- Match skills section to job requirements
- Keep same structure, optimize every line
Job Type: {req.job_type}
Job Description: {req.job_description}
Original Resume: {source_resume_text}
Return JSON only:
{{"rewritten": "...", "changes_made": [], "keywords_added": [], "keywords_removed": []}}"""

    raw_response = llm.ask("You are a precise resume optimization assistant.", prompt)
    parsed = _extract_json(raw_response, {})
    rewritten = str(parsed.get("rewritten", "")).strip()
    fallback_reason = ""

    if raw_response.strip().lower().startswith("ai error:"):
        fallback_reason = "AI provider was unavailable; generated a structured rewrite from your profile and job description."
        rewritten = ""
    if not rewritten:
        rewritten = _normalize_rewritten_text(raw_response)
    rewritten, nested_payload = _unwrap_nested_rewrite_payload(rewritten)
    if not rewritten:
        fallback_reason = fallback_reason or "AI returned an empty response; generated a structured rewrite from your profile and job description."
    lowered_rewrite = rewritten.lower() if rewritten else ""
    if rewritten and (lowered_rewrite.startswith("i cannot") or lowered_rewrite.startswith("i can't") or "cannot provide a rewritten resume" in lowered_rewrite):
        fallback_reason = "AI returned a refusal response; generated a structured rewrite from your profile and job description."
        rewritten = ""
    if rewritten and _is_placeholder_rewrite(rewritten):
        fallback_reason = "AI returned a placeholder response; generated a structured rewrite from your profile and job description."
        rewritten = ""
    if not rewritten:
        rewritten = _build_resume_fallback(source_resume_text, req.job_description or "", req.job_type or "General")

    changes_source = parsed.get("changes_made") or nested_payload.get("changes_made") or []
    added_source = parsed.get("keywords_added") or nested_payload.get("keywords_added") or []
    removed_source = parsed.get("keywords_removed") or nested_payload.get("keywords_removed") or []

    changes_made = [str(item) for item in changes_source if str(item).strip()]
    keywords_added = [str(item) for item in added_source if str(item).strip()]
    keywords_removed = [str(item) for item in removed_source if str(item).strip()]

    if not changes_made:
        auto_changes, auto_added, auto_removed = _build_change_hints(source_resume_text, rewritten, req.job_description or "")
        changes_made = auto_changes
        if not keywords_added:
            keywords_added = auto_added
        if not keywords_removed:
            keywords_removed = auto_removed
    if fallback_reason:
        changes_made.insert(0, fallback_reason)

    return ResumeRewriteResponse(
        rewritten=rewritten,
        changes_made=changes_made,
        keywords_added=keywords_added,
        keywords_removed=keywords_removed,
    )


@router.post("/versions", response_model=ResumeVersionOut)
def create_resume_version(payload: ResumeVersionCreate, db: Session = Depends(get_db)):
    version = ResumeVersion(
        name=payload.name,
        job_type=payload.job_type,
        content=payload.content,
        used_for=payload.used_for,
        ats_score=payload.ats_score,
    )
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


@router.get("/versions", response_model=list[ResumeVersionOut])
def list_resume_versions(db: Session = Depends(get_db)):
    return db.query(ResumeVersion).order_by(ResumeVersion.created_at.desc()).all()


@router.get("/versions/{version_id}", response_model=ResumeVersionOut)
def get_resume_version(version_id: int, db: Session = Depends(get_db)):
    version = db.query(ResumeVersion).filter(ResumeVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Resume version not found")
    return version


@router.delete("/versions/{version_id}")
def delete_resume_version(version_id: int, db: Session = Depends(get_db)):
    version = db.query(ResumeVersion).filter(ResumeVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Resume version not found")
    db.delete(version)
    db.commit()
    return {"success": True}


@router.patch("/versions/{version_id}", response_model=ResumeVersionOut)
def update_resume_version_used_for(
    version_id: int,
    payload: ResumeVersionUpdateUsedFor,
    db: Session = Depends(get_db),
):
    version = db.query(ResumeVersion).filter(ResumeVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Resume version not found")

    version.used_for = payload.used_for
    db.commit()
    db.refresh(version)
    return version
