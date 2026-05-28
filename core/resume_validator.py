from __future__ import annotations

import re
from typing import Any

from core.resume_standards import COMMON_JOB_KEYWORDS, PROHIBITED_ELEMENTS, RESUME_STANDARD_HEADINGS


KEYWORD_DENSITY_WARNING_THRESHOLD = float(__import__("os").getenv("KEYWORD_DENSITY_WARNING_THRESHOLD", "0.30") or 0.30)


def _normalize(text: str | None) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def _keyword_density(text: str, keywords: list[str]) -> float:
    cleaned = re.findall(r"[A-Za-z][A-Za-z0-9+.#/-]{1,}", text.lower())
    if not cleaned:
        return 0.0
    keyword_hits = 0
    for keyword in keywords:
        if not keyword:
            continue
        keyword_hits += len(re.findall(rf"\b{re.escape(keyword.lower())}\b", text.lower()))
    return keyword_hits / max(1, len(cleaned))


def validate_resume_output(resume_text: str, html_resume: str, job_description: str = "") -> dict[str, Any]:
    warnings: list[str] = []
    suggestions: list[str] = []
    text = resume_text or ""
    html = html_resume or ""

    normalized_text = _normalize(text)

    missing_headings = [heading for heading in RESUME_STANDARD_HEADINGS if heading.lower() not in normalized_text]
    if missing_headings:
        warnings.append(f"Missing standard headings: {', '.join(missing_headings)}")

    forbidden_hits: list[str] = []
    html_lower = html.lower()
    for forbidden in PROHIBITED_ELEMENTS:
        if forbidden == "tables" and ("<table" in html_lower or "table-layout" in html_lower):
            forbidden_hits.append("tables")
        elif forbidden == "columns" and ("column-count" in html_lower or "columns:" in html_lower):
            forbidden_hits.append("columns")
        elif forbidden == "images" and "<img" in html_lower:
            forbidden_hits.append("images")
        elif forbidden == "headers" and "<header" in html_lower:
            forbidden_hits.append("headers")
        elif forbidden == "footers" and "<footer" in html_lower:
            forbidden_hits.append("footers")

    if forbidden_hits:
        warnings.append(f"Forbidden layout elements detected: {', '.join(sorted(set(forbidden_hits)))}")

    density = _keyword_density(text, COMMON_JOB_KEYWORDS)
    if density >= KEYWORD_DENSITY_WARNING_THRESHOLD:
        suggestions.append("Consider reducing repetition of keywords; the resume reads a bit dense.")
    elif job_description.strip() and density < 0.01:
        warnings.append("Keyword density is very low for the target job description.")

    passed = not warnings
    message = "Your resume passed ATS validation." if passed else warnings[0]
    if suggestions and passed:
        message = suggestions[0]
    return {
        "passed": passed,
        "warnings": warnings,
        "suggestions": suggestions,
        "message": message,
        "keyword_density": round(density, 4),
    }
