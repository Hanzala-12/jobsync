from __future__ import annotations

from dataclasses import is_dataclass, asdict
from datetime import date, datetime
from typing import Any, Iterable, Mapping
import json
import re


SECTION_ORDER = [
    "Summary",
    "Skills",
    "Experience",
    "Education",
    "Projects",
    "Certifications",
    "Languages",
    "Achievements",
]


def _value(source: Any, key: str, default: Any = None) -> Any:
    if source is None:
        return default
    if isinstance(source, Mapping):
        return source.get(key, default)
    if is_dataclass(source):
        return asdict(source).get(key, default)
    return getattr(source, key, default)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def parse_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = list(value)
    elif isinstance(value, str):
        raw = value.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
                if isinstance(parsed, list):
                    items = parsed
                else:
                    items = [raw]
            except Exception:
                items = re.split(r"[,;|\n]+", raw)
        else:
            items = re.split(r"[,;|\n]+", raw)
    else:
        items = [value]

    cleaned: list[str] = []
    seen: set[str] = set()
    for item in items:
        text = _as_text(item)
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(text)
    return cleaned


def parse_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def parse_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except Exception:
        return None


def parse_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def format_date(value: Any) -> str:
    if not value:
        return ""
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return _as_text(value)


def format_year_range(start_year: Any, end_year: Any) -> str:
    start = parse_int(start_year)
    end = parse_int(end_year)
    if start and end:
        return f"{start}-{end}"
    if start:
        return f"{start}"
    if end:
        return f"Until {end}"
    return ""


def build_profile_resume_text(profile: Any, *, job_title: str | None = None, company: str | None = None,
                              education: Iterable[Any] | None = None,
                              work_experience: Iterable[Any] | None = None,
                              certifications: Iterable[Any] | None = None,
                              projects: Iterable[Any] | None = None,
                              languages: Iterable[Any] | None = None) -> str:
    full_name = _as_text(_value(profile, "full_name") or _value(profile, "name"))
    email = _as_text(_value(profile, "email") or _value(profile, "user_email"))
    phone = _as_text(_value(profile, "phone"))
    location = _as_text(_value(profile, "location"))
    linkedin_url = _as_text(_value(profile, "linkedin_url"))
    portfolio_url = _as_text(_value(profile, "portfolio_url"))
    summary = _as_text(_value(profile, "summary"))
    skills = parse_string_list(_value(profile, "skills"))
    achievements = parse_string_list(_value(profile, "achievements"))
    preferred_titles = parse_string_list(_value(profile, "preferred_job_titles"))

    parts: list[str] = []
    header_bits = [bit for bit in [full_name, location] if bit]
    if header_bits:
        parts.append(" | ".join(header_bits))
    contact_bits = [bit for bit in [email, phone, linkedin_url, portfolio_url] if bit]
    if contact_bits:
        parts.append(f"Contact: {' | '.join(contact_bits)}")
    if summary:
        parts.append(f"Summary: {summary}")
    elif job_title or company:
        target = f"{job_title or 'the role'} at {company or 'the company'}"
        parts.append(f"Summary: Tailored for {target}.")
    if skills:
        parts.append(f"Skills: {', '.join(skills)}")
    if preferred_titles:
        parts.append(f"Target Roles: {', '.join(preferred_titles)}")

    def _format_multiline_section(title: str, items: Iterable[Any], renderer) -> None:
        normalized_items = list(items or [])
        if not normalized_items:
            return
        parts.append(f"{title}:")
        for item in normalized_items:
            rendered = renderer(item)
            if rendered:
                parts.append(f"- {rendered}")

    _format_multiline_section(
        "Education",
        education or _value(profile, "education") or [],
        lambda item: " | ".join(
            bit for bit in [
                _as_text(_value(item, "degree")),
                _as_text(_value(item, "institution")),
                _as_text(_value(item, "field_of_study")),
                format_year_range(_value(item, "start_year"), _value(item, "end_year")),
                f"GPA {_value(item, 'gpa')}" if _value(item, "gpa") not in (None, "") else "",
            ] if bit
        ),
    )
    _format_multiline_section(
        "Experience",
        work_experience or _value(profile, "work_experience") or [],
        lambda item: " | ".join(
            bit for bit in [
                _as_text(_value(item, "job_title")),
                _as_text(_value(item, "company")),
                format_date(_value(item, "start_date")) + (f" to {format_date(_value(item, 'end_date'))}" if _value(item, "end_date") else ""),
            ] if bit
        ),
    )
    if work_experience or _value(profile, "work_experience"):
        for item in (work_experience or _value(profile, "work_experience") or []):
            responsibilities = parse_string_list(_value(item, "responsibilities"))
            achievements_text = parse_string_list(_value(item, "achievements"))
            if responsibilities:
                for entry in responsibilities:
                    parts.append(f"- Responsibility: {entry}")
            if achievements_text:
                for entry in achievements_text:
                    parts.append(f"- Achievement: {entry}")

    _format_multiline_section(
        "Projects",
        projects or _value(profile, "projects") or [],
        lambda item: " | ".join(
            bit for bit in [
                _as_text(_value(item, "name")),
                _as_text(_value(item, "description")),
                f"Technologies: {', '.join(parse_string_list(_value(item, 'technologies')))}" if parse_string_list(_value(item, "technologies")) else "",
                _as_text(_value(item, "project_url")),
            ] if bit
        ),
    )
    _format_multiline_section(
        "Certifications",
        certifications or _value(profile, "certifications") or [],
        lambda item: " | ".join(
            bit for bit in [
                _as_text(_value(item, "name")),
                _as_text(_value(item, "issuing_org")),
                format_date(_value(item, "date_earned")),
                _as_text(_value(item, "credential_url")),
            ] if bit
        ),
    )
    _format_multiline_section(
        "Languages",
        languages or _value(profile, "languages") or [],
        lambda item: " | ".join(
            bit for bit in [
                _as_text(_value(item, "name")),
                _as_text(_value(item, "proficiency")),
            ] if bit
        ),
    )
    if achievements:
        parts.append("Achievements:")
        for item in achievements:
            parts.append(f"- {item}")

    return "\n".join(part for part in parts if _as_text(part)).strip()


def profile_completeness(profile: Any) -> int:
    checks = [
        bool(_as_text(_value(profile, "full_name"))),
        bool(_as_text(_value(profile, "email"))),
        bool(_as_text(_value(profile, "location"))),
        bool(_as_text(_value(profile, "summary"))),
        bool(parse_string_list(_value(profile, "skills"))),
        bool(parse_string_list(_value(profile, "preferred_job_titles"))),
        bool(_value(profile, "desired_salary_min") not in (None, "") or _value(profile, "desired_salary_max") not in (None, "")),
        bool(parse_bool(_value(profile, "willing_to_relocate"), False)),
        bool(_as_text(_value(profile, "preferred_work_location"))),
        bool(list(_value(profile, "education") or [])),
        bool(list(_value(profile, "work_experience") or [])),
        bool(list(_value(profile, "certifications") or [])),
        bool(list(_value(profile, "projects") or [])),
        bool(list(_value(profile, "languages") or [])),
    ]
    score = round((sum(1 for check in checks if check) / len(checks)) * 100)
    return max(0, min(100, score))
