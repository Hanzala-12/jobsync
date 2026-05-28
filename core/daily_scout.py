"""Daily Scout automated job hunting task."""

from datetime import datetime
from typing import Any, Dict

from backend.models import UserProfile
from backend.services.job_apis import search_jobs
from core.database import get_db
from core.deduplicator import process_incoming_job
from core.normalizer import normalize_job

SCOUT_STATE: Dict[str, Any] = {
    "running": False,
    "progress": 0,
    "message": "Idle",
    "last_run": None,
    "error": None,
    "results": [],
}


def _keywords(text: str) -> set[str]:
    import re

    stop = {"the", "and", "for", "with", "this", "that", "from", "your", "you", "are", "job", "work"}
    return {word for word in re.findall(r"[a-z0-9+#.]+", (text or "").lower()) if len(word) > 2 and word not in stop}


def _score_jobs_fast(resume_text: str, jobs: list, role: str, skills: str, min_score: int) -> list:
    resume_terms = _keywords(resume_text)
    target_terms = _keywords(f"{role} {skills}")
    scored = []

    for job in jobs:
        title_terms = _keywords(job.get("title", ""))
        description_terms = _keywords(job.get("description", ""))
        job_terms = title_terms | description_terms

        target_hits = len(target_terms & job_terms)
        resume_hits = len(resume_terms & job_terms)
        title_hits = len(target_terms & title_terms)

        score = 45 + (title_hits * 15) + (target_hits * 6) + min(resume_hits * 3, 20)
        if job.get("source") in {"rozee", "adzuna", "google_indexed", "mustakbil", "brightspyre", "bing_jobs", "linkedin", "careers_page"}:
            score += 10
        score = max(0, min(100, score))

        job["match_score"] = score
        job["missing_skills"] = sorted(list(target_terms - job_terms))[:6]
        job["match_analysis"] = "Fast local score based on role, skill, title, and resume keyword overlap."
        if score >= min_score:
            scored.append(job)

    if not scored and jobs:
        scored = sorted(jobs, key=lambda item: item.get("match_score", 0), reverse=True)[:5]

    return sorted(scored, key=lambda item: item.get("match_score", 0), reverse=True)


def _set_state(**updates):
    SCOUT_STATE.update(updates)


def get_scout_status() -> dict:
    return dict(SCOUT_STATE)


def run_daily_scout(role="software engineer", location="Pakistan", skills="", min_score=75, page=1, user_id: int | None = None) -> dict:
    """Fetch jobs, score against resume, and save top matches."""
    db = next(get_db())

    try:
        _set_state(running=True, progress=5, message="Preparing scout", error=None, results=[])

        # Load user's selected profile resume_text when user_id is provided
        resume_text = ""
        try:
            if user_id:
                # Find selected profile id from user_preferences table
                from backend.models import UserPreference, UserProfile

                pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).order_by(UserPreference.updated_at.desc(), UserPreference.id.desc()).first()
                selected_id = pref.selected_profile_id if pref else None
                profile = None
                if selected_id:
                    profile = db.query(UserProfile).filter(UserProfile.id == selected_id, UserProfile.user_id == user_id).first()
                if not profile:
                    # Fallback to most recent profile for the user
                    profile = (
                        db.query(UserProfile)
                        .filter(UserProfile.user_id == user_id)
                        .order_by(UserProfile.created_at.desc(), UserProfile.id.desc())
                        .first()
                    )
                if profile and getattr(profile, "resume_text", None):
                    resume_text = profile.resume_text or ""
        except Exception:
            resume_text = ""

        _set_state(progress=35, message="Searching live jobs")
        search_query = " ".join(part for part in [role, skills] if part and part.strip())
        remote_only = location.strip().lower() == "remote"
        jobs = search_jobs(query=search_query or role, location=location, remote_only=remote_only)

        if not jobs:
            _set_state(running=False, progress=100, message="No jobs found", error="No jobs found. Try a different query.")
            return {"error": "No jobs found. Try a different query."}

        _set_state(progress=55, message="Scoring jobs against resume")
        matches = _score_jobs_fast(resume_text, jobs, role, skills, min_score)

        saved_ids = []
        duplicate_count = 0

        for job in matches:
            normalized = normalize_job(
                {
                    "title": job.get("title", ""),
                    "company": job.get("company", ""),
                    "city": job.get("city") or job.get("location") or location,
                    "location": job.get("location", ""),
                    "description": job.get("description", ""),
                    "apply_url": job.get("apply_url") or job.get("url") or "",
                    "url": job.get("url") or job.get("apply_url") or "",
                    "posted_date": job.get("posted_date", ""),
                    "salary": job.get("salary", ""),
                    "external_id": str(job.get("external_id") or job.get("url") or "").strip() or None,
                },
                job.get("source") or "daily-scout",
            )
            saved_job, action = process_incoming_job(db, normalized)
            if action != "created":
                duplicate_count += 1
            else:
                saved_ids.append(saved_job.id)
                if resume_text and saved_job.id:
                    try:
                        from core.rag_service import generate_cover_letter_with_rag, save_cover_letter_artifacts

                        draft, source_ids, retrieved_chunks = generate_cover_letter_with_rag(
                            saved_job.description or job.get("description", ""),
                            resume_text[:1500],
                            company_name=saved_job.company or job.get("company", ""),
                            role=saved_job.title or job.get("title", ""),
                            tone="professional",
                            top_k=5,
                        )
                        save_cover_letter_artifacts(
                            saved_job.id,
                            draft,
                            source_ids,
                            retrieved_chunks,
                            metadata={
                                "company": saved_job.company,
                                "role": saved_job.title,
                                "source": saved_job.source,
                                "job_url": saved_job.url,
                                "generated_by": "daily_scout",
                            },
                        )
                    except Exception:
                        pass

        discovered_jobs = [
            {
                "id": job.get("external_id") or job.get("id"),
                "title": job.get("title"),
                "company": job.get("company"),
                "location": job.get("location"),
                "description": job.get("description"),
                "url": job.get("url"),
                "posted": job.get("posted_date"),
                "match_score": job.get("match_score", 0),
                "source": job.get("source", "daily-scout"),
                "missing_skills": job.get("missing_skills", []),
            }
            for job in matches
        ]

        _set_state(
            running=False,
            progress=100,
            message="Scout complete",
            last_run=datetime.now().isoformat(),
            results=discovered_jobs,
            error=None,
        )

        return {
            "success": True,
            "found": len(matches),
            "saved": len(saved_ids),
            "duplicates_skipped": duplicate_count,
            "discovered_jobs": discovered_jobs,
            "top_jobs": [
                {"title": item["title"], "company": item["company"], "score": item["match_score"]}
                for item in discovered_jobs[:5]
            ],
        }

    except Exception as exc:
        _set_state(running=False, progress=100, message="Scout failed", error=str(exc))
        return {"error": str(exc)}
    finally:
        db.close()
