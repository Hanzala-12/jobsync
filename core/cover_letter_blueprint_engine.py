from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from backend.services.profile_data import parse_string_list


_BLUEPRINT_PATH = Path(__file__).resolve().parents[1] / "blueprints" / "cover_letter_blueprint.json"
_CACHE_TTL_SECONDS = 3600
_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}


class _SafeFormatDict(dict[str, Any]):
    def __missing__(self, key: str) -> str:
        return ""


def _text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or default
    if isinstance(value, (list, tuple, set)):
        items = [str(item).strip() for item in value if str(item).strip()]
        return ", ".join(items) if items else default
    return str(value).strip() or default


@lru_cache(maxsize=1)
def load_blueprint() -> dict[str, Any]:
    with _BLUEPRINT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _first_work_experience(profile: Any) -> Any:
    work_experience = getattr(profile, "work_experience", None) or []
    return work_experience[0] if work_experience else None


def _pick_previous_company(profile: Any, company: str) -> str:
    experience = _first_work_experience(profile)
    previous_company = _text(getattr(experience, "company", None))
    if previous_company:
        return previous_company
    return company or "my previous team"


def _pick_achievement(profile: Any, job_description: str) -> str:
    experience = _first_work_experience(profile)
    if experience:
        achievements = parse_string_list(getattr(experience, "achievements", None))
        if achievements:
            return achievements[0].rstrip(".") + "."

        responsibilities = parse_string_list(getattr(experience, "responsibilities", None))
        if responsibilities:
            first = responsibilities[0].rstrip(".")
            if first.lower().startswith(("led ", "built ", "improved ", "designed ", "shipped ")):
                return first + "."
            return f"contributed to {first.lower()}."

    profile_achievements = parse_string_list(getattr(profile, "achievements", None))
    if profile_achievements:
        return profile_achievements[0].rstrip(".") + "."

    job_hint = _text(job_description)
    if job_hint:
        words = re.findall(r"[A-Za-z][A-Za-z0-9+#.-]{2,}", job_hint)
        if words:
            return f"delivered strong results relevant to {words[0].lower()}."

    return "delivered strong results."


def _pick_skills(profile: Any, job_description: str) -> str:
    skills = parse_string_list(getattr(profile, "skills", None))
    if skills:
        return ", ".join(skills[:5])

    if job_description:
        words = [
            word
            for word in re.findall(r"\b[A-Za-z][A-Za-z0-9+#.-]{2,}\b", job_description)
            if word.lower() not in {"responsibilities", "required", "preferably", "experience"}
        ]
        if words:
            return ", ".join(dict.fromkeys(words[:5]))

    return "my core professional experience"


def build_cover_letter_context(profile: Any, request: Mapping[str, Any]) -> dict[str, str]:
    role = _text(request.get("role") or request.get("job_title"), "the role")
    company = _text(request.get("company"), "your company")
    job_description = _text(request.get("job_description") or request.get("description"))

    return {
        "job_title": role,
        "company": company,
        "skills": _pick_skills(profile, job_description),
        "previous_company": _pick_previous_company(profile, company),
        "achievement": _pick_achievement(profile, job_description),
    }


def fill_blueprint(blueprint: Mapping[str, Any], data: Mapping[str, Any]) -> dict[str, Any]:
    placeholders = _SafeFormatDict({key: _text(value) for key, value in data.items()})
    sections: list[dict[str, str]] = []
    rendered_parts: list[str] = []

    for section in blueprint.get("sections", []):
        name = _text(section.get("name"))
        template = _text(section.get("template"))
        rendered = template.format_map(placeholders)
        sections.append({"name": name, "text": rendered})
        rendered_parts.append(rendered)

    return {
        "sections": sections,
        "text": "\n\n".join(rendered_parts).strip(),
    }


def _rebuild_text(sections: list[dict[str, str]]) -> str:
    return "\n\n".join(section["text"] for section in sections if _text(section.get("text"))).strip()


async def enhance_with_llm(filled_text: Any, job_description: str) -> Any:
    payload = copy.deepcopy(filled_text) if isinstance(filled_text, dict) else {"text": _text(filled_text), "sections": []}
    sections = payload.get("sections") or []
    body = next((section for section in sections if _text(section.get("name")) == "body"), None)
    if not body:
        return filled_text

    try:
        from core.llm_provider import LLMProvider
    except Exception:
        return filled_text

    provider = LLMProvider()
    if provider.fallback_mode or not provider.backends:
        return filled_text

    system_prompt = (
        "Rewrite the BODY paragraph of a cover letter so it sounds natural, specific, and concise. "
        "Keep it to one or two sentences, keep the meaning aligned to the job description, and return only the revised paragraph."
    )
    user_prompt = (
        f"Job description:\n{_text(job_description)[:3000]}\n\n"
        f"Current body paragraph:\n{_text(body.get('text'))}\n\n"
        "Return only the rewritten body paragraph."
    )

    try:
        revised_body = await asyncio.wait_for(
            asyncio.to_thread(provider.ask, system_prompt, user_prompt, 0.2),
            timeout=1.0,
        )
    except Exception:
        return filled_text

    revised_body = _text(revised_body)
    if not revised_body:
        return filled_text

    body["text"] = revised_body
    payload["text"] = _rebuild_text(sections)
    return payload


def _cache_key(user_id: int, request: Mapping[str, Any]) -> str:
    raw = "|".join(
        [
            str(user_id),
            _text(request.get("role") or request.get("job_title")),
            _text(request.get("company")),
            _text(request.get("job_description") or request.get("description")),
            _text(request.get("tone"), "professional"),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _cache_get(key: str) -> dict[str, Any] | None:
    entry = _CACHE.get(key)
    if not entry:
        return None
    expires_at, payload = entry
    if expires_at < time.time():
        _CACHE.pop(key, None)
        return None
    return copy.deepcopy(payload)


def _cache_set(key: str, payload: dict[str, Any]) -> None:
    _CACHE[key] = (time.time() + _CACHE_TTL_SECONDS, copy.deepcopy(payload))


async def generate_cover_letter_draft(profile: Any, request: Mapping[str, Any]) -> dict[str, Any]:
    cache_key = _cache_key(getattr(profile, "user_id", 0) or 0, request)
    cached = _cache_get(cache_key)
    if cached:
        return cached

    blueprint = load_blueprint()
    context = build_cover_letter_context(profile, request)
    filled = fill_blueprint(blueprint, context)
    enhanced = await enhance_with_llm(filled, _text(request.get("job_description") or request.get("description")))

    if not isinstance(enhanced, dict):
        enhanced = filled

    payload = {
        "draft": _text(enhanced.get("text")),
        "source_ids": ["blueprint"],
        "sections": enhanced.get("sections") or filled.get("sections") or [],
    }
    _cache_set(cache_key, payload)
    return copy.deepcopy(payload)