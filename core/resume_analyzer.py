from __future__ import annotations

import re
import json
from dataclasses import dataclass
from typing import Any, Iterable

from core.llm_provider import LLMProvider
from core.resume_standards import COMMON_JOB_KEYWORDS, DEFAULT_SKILLS_BLOCK, RESUME_STANDARD_HEADINGS, SECTION_ALIASES, WEAK_PHRASE_REPLACEMENTS


STOP_WORDS = {
    "the",
    "and",
    "for",
    "with",
    "that",
    "this",
    "from",
    "your",
    "you",
    "are",
    "was",
    "were",
    "have",
    "has",
    "had",
    "will",
    "can",
    "not",
    "but",
    "our",
    "their",
    "they",
    "them",
    "its",
    "into",
    "about",
    "role",
    "job",
    "work",
    "using",
    "use",
    "used",
    "over",
    "under",
    "than",
    "then",
    "also",
    "while",
    "where",
    "when",
    "which",
    "through",
    "across",
    "within",
    "closely",
    "team",
    "teams",
}

NOISE_KEYWORDS = {
    "senior",
    "junior",
    "mid",
    "level",
    "full",
    "time",
    "full-time",
    "part",
    "remote",
    "hybrid",
    "company",
    "role",
    "position",
    "experience",
    "working",
    "work",
    "team",
    "teams",
    "candidate",
    "backend",
    "frontend",
    "fullstack",
    "software",
    "engineer",
    "engineering",
    "developer",
    "development",
    "strong",
    "excellent",
    "proven",
    "robust",
}


@dataclass
class ResumeSection:
    title: str
    lines: list[str]


def _clean_text(text: str | None) -> str:
    return re.sub(r"\n{3,}", "\n\n", (text or "").replace("\r\n", "\n")).strip()


def _remove_duplicate_paragraphs(text: str | None) -> str:
    if not text:
        return ""

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part and part.strip()]
    seen: set[str] = set()
    unique: list[str] = []

    for paragraph in paragraphs:
        key = re.sub(r"\s+", " ", paragraph).strip().lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(paragraph)

    return _clean_text("\n\n".join(unique))


def _tokenize(text: str) -> list[str]:
    return re.findall(r"[A-Za-z][A-Za-z0-9+.#/-]{1,}", (text or "").lower())


def _keyword_key(keyword: str) -> str:
    return re.sub(r"\s+", " ", keyword.lower()).strip()


def _extract_keywords(job_description: str) -> list[str]:
    text = _clean_text(job_description).lower()
    if not text:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    for keyword in COMMON_JOB_KEYWORDS:
        if keyword in text and _keyword_key(keyword) not in seen:
            seen.add(_keyword_key(keyword))
            candidates.append(keyword)

    tokens = [token for token in _tokenize(text) if token not in STOP_WORDS and token not in NOISE_KEYWORDS and len(token) >= 3]
    frequencies: dict[str, int] = {}
    for token in tokens:
        frequencies[token] = frequencies.get(token, 0) + 1

    ranked_tokens = [token for token, count in sorted(frequencies.items(), key=lambda item: (-item[1], item[0])) if count > 1]
    for token in ranked_tokens[:20]:
        if token not in seen:
            seen.add(token)
            candidates.append(token)

    phrases = []
    for window in (2, 3):
        for idx in range(len(tokens) - window + 1):
            phrase = " ".join(tokens[idx : idx + window])
            phrase_words = phrase.split()
            if any(word in STOP_WORDS or word in NOISE_KEYWORDS for word in phrase_words):
                continue
            if phrase in text and phrase not in seen:
                seen.add(phrase)
                phrases.append(phrase)

    ordered: list[str] = []
    for item in candidates + phrases:
        normalized = item.strip()
        if not normalized:
            continue
        if normalized.lower() in NOISE_KEYWORDS:
            continue
        if normalized not in ordered:
            ordered.append(normalized)

    return ordered[:20]


def _keyword_hits(text: str, keywords: Iterable[str]) -> set[str]:
    lowered = (text or "").lower()
    hits: set[str] = set()
    for keyword in keywords:
        if not keyword:
            continue
        pattern = rf"\b{re.escape(keyword.lower())}\b"
        if re.search(pattern, lowered):
            hits.add(keyword)
    return hits


def _count_quantified_achievements(text: str) -> int:
    patterns = [r"\b\d+(?:\.\d+)?%\b", r"\$\d+[\d,]*(?:\.\d+)?", r"\b\d+[\d,]*\b"]
    return sum(len(re.findall(pattern, text)) for pattern in patterns)


def _weak_phrase_hits(text: str) -> list[tuple[str, str]]:
    lowered = text.lower()
    hits: list[tuple[str, str]] = []
    for weak, strong in WEAK_PHRASE_REPLACEMENTS.items():
        if weak in lowered:
            hits.append((weak, strong))
    return hits


def _normalize_resume_format(text: str) -> str:
    """Normalize resume text formatting for clean bullets and spacing."""
    raw = _clean_text(text)
    if not raw:
        return ""

    # Undo common escaped characters produced by LLM responses.
    raw = raw.replace("\\n", "\n")
    raw = re.sub(r"\\([\-•])", r"\1", raw)

    lines: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            lines.append("")
            continue

        # Normalize bullets to "- " or "• " with a required space after marker.
        if re.match(r"^[-•]\S", stripped):
            stripped = f"{stripped[0]} {stripped[1:].strip()}"
        elif re.match(r"^[-•]\s+", stripped):
            stripped = f"{stripped[0]} {stripped[1:].strip()}"

        # Collapse noisy whitespace inside a line.
        stripped = re.sub(r"\s{2,}", " ", stripped)
        lines.append(stripped)

    return _clean_text("\n".join(lines))


def _ensure_priority_keywords(text: str, priority_keywords: list[str], min_count: int = 3) -> str:
    """Ensure at least `min_count` priority keywords appear in the resume text.

    The keywords are appended to the Skills line if missing.
    """
    if not text:
        return text

    def _has_kw(body: str, kw: str) -> bool:
        pattern_kw = re.escape(kw).replace(r"\ ", r"\s+")
        return bool(re.search(rf"\b{pattern_kw}\b", body, flags=re.IGNORECASE))

    cleaned = _normalize_resume_format(text)
    present = [kw for kw in priority_keywords if _has_kw(cleaned, kw)]
    if len(present) >= min_count:
        return cleaned

    needed: list[str] = []
    for kw in priority_keywords:
        if kw not in present:
            needed.append(kw)
        if len(present) + len(needed) >= min_count:
            break

    if not needed:
        return cleaned

    lines = cleaned.splitlines()
    skills_idx = None
    for idx, line in enumerate(lines):
        if line.strip().lower() == "skills":
            skills_idx = idx
            break

    if skills_idx is not None:
        # Find first non-empty content line after "Skills" heading.
        content_idx = None
        for idx in range(skills_idx + 1, len(lines)):
            if lines[idx].strip():
                content_idx = idx
                break
        if content_idx is not None:
            existing = [part.strip() for part in re.split(r"\s*,\s*", lines[content_idx]) if part.strip()]
            existing_lower = {item.lower() for item in existing}
            for kw in needed:
                if kw.lower() not in existing_lower:
                    existing.append(kw)
                    existing_lower.add(kw.lower())
            lines[content_idx] = ", ".join(existing)
        else:
            lines.insert(skills_idx + 1, ", ".join(needed))
    else:
        # Append a Skills section if missing entirely.
        lines.extend(["", "Skills", ", ".join(needed)])

    return _normalize_resume_format("\n".join(lines))


def _assemble_resume(sections: list[ResumeSection]) -> str:
    """Render parsed resume sections back into clean plain-text resume format."""
    parts: list[str] = []
    for section in sections:
        title = section.title.strip()
        lines = [line.strip() for line in section.lines if line.strip()]
        if not title or not lines:
            continue

        if title == "Summary":
            parts.append("Summary\n" + "\n".join(lines))
            continue

        parts.append(title)
        parts.extend(lines)

    return _normalize_resume_format("\n\n".join(parts))


def _upgrade_title_line(line: str, _ctx: list[str]) -> str:
    """Normalize or upgrade a raw title/header line for experience entries.

    Simple fallback that returns the stripped line; kept as a small helper
    to preserve compatibility with earlier code paths.
    """
    return str(line).strip()


def _parse_sections(resume_text: str) -> list[ResumeSection]:
    lines = [line.rstrip() for line in _clean_text(resume_text).splitlines()]
    sections: list[ResumeSection] = []
    current_title = "Summary"
    current_lines: list[str] = []

    # Build a canonical mapping using known aliases (SECTION_ALIASES) and defaults
    canonical = {k.lower(): v for k, v in SECTION_ALIASES.items()}
    # Ensure common headings are present
    for hdr in ("summary", "skills", "experience", "education", "projects", "certifications", "languages", "contact"):
        canonical.setdefault(hdr, hdr.title())

    def flush() -> None:
        nonlocal current_title, current_lines
        if current_lines:
            sections.append(ResumeSection(current_title, current_lines))
            current_title = "Summary"
        current_lines = []

    for raw in lines:
        stripped = raw.strip()
        if not stripped:
            flush()
            continue

        lowered = stripped.lower().rstrip(":")
        if lowered in canonical:
            flush()
            current_title = canonical[lowered]
            continue

        # Match headings that start with a canonical word, e.g. 'Summary:', 'Work Experience', etc.
        m = re.match(r"^([A-Za-z ]{3,40})[:]?", stripped)
        if m:
            candidate = m.group(1).strip().lower()
            if candidate in canonical:
                flush()
                current_title = canonical[candidate]
                continue
            # Fallback: if the first word is one of known canonical keys, use it
            first_word = candidate.split()[0]
            if first_word in canonical:
                flush()
                current_title = canonical[first_word]
                continue

        current_lines.append(stripped)

    flush()
    return sections


def _score_resume(resume_text: str, job_description: str, keywords: list[str], missing_keywords: list[str]) -> int:
    normalized = resume_text.lower()
    job_keywords = keywords or _extract_keywords(job_description)
    match_count = len(_keyword_hits(normalized, job_keywords))
    keyword_ratio = match_count / max(1, len(job_keywords[:15]))
    keyword_score = min(45, round(keyword_ratio * 45))

    section_hits = sum(1 for heading in RESUME_STANDARD_HEADINGS if heading.lower() in normalized)
    section_score = round((section_hits / len(RESUME_STANDARD_HEADINGS)) * 20)

    quant_score = min(20, _count_quantified_achievements(resume_text) * 4)

    weak_hits = len(_weak_phrase_hits(resume_text))
    language_score = max(0, 15 - weak_hits * 3)

    penalty = min(20, len(missing_keywords) * 2)
    score = keyword_score + section_score + quant_score + language_score - penalty
    return max(0, min(100, int(round(score))))


def _extract_sections_for_output(resume_text: str) -> dict[str, Any]:
    sections = _parse_sections(resume_text)
    contact_lines: list[str] = []
    summary = ""
    skills: list[str] = []
    experience: list[dict[str, Any]] = []
    education: list[str] = []
    projects: list[str] = []

    for section in sections:
        title = section.title
        lines = [line.strip() for line in section.lines if line.strip()]
        if title == "Summary":
            summary = " ".join(lines)
            continue
        if title == "Contact":
            contact_lines.extend(lines)
            continue
        if title == "Skills":
            skills.extend([part.strip() for line in lines for part in re.split(r"[,;|•]", line) if part.strip()])
            continue
        if title == "Experience":
            current_item: dict[str, Any] | None = None
            for line in lines:
                if not line.startswith(("-", "•")):
                    if current_item:
                        experience.append(current_item)
                    current_item = {"title": _upgrade_title_line(line, []), "bullets": []}
                else:
                    if current_item is None:
                        current_item = {"title": "Experience", "bullets": []}
                    current_item.setdefault("bullets", []).append(line.lstrip("-• ").strip())
            if current_item:
                experience.append(current_item)
            continue
        if title == "Education":
            education.extend(lines)
            continue
        if title == "Projects":
            projects.extend(lines)
            continue

    return {
        "contact_lines": contact_lines,
        "summary": summary,
        "skills": skills,
        "experience": experience,
        "education": education,
        "projects": projects,
    }


def analyze_and_fix_resume(resume_text: str, job_description: str, structured_profile: dict | None = None, job_title: str | None = None) -> dict[str, Any]:
    original_resume = _clean_text(resume_text)
    job_description = _clean_text(job_description)
    job_keywords = _extract_keywords(job_description)
    original_hits = _keyword_hits(original_resume, job_keywords)
    missing_keywords = [keyword for keyword in job_keywords if keyword not in original_hits]

    def _llm_polish_resume(resume_text: str, job_description: str, keywords: list[str], structured_profile: dict | None = None, job_title: str | None = None) -> str | None:
        provider = LLMProvider()
        if not provider.backends:
            return None

        def _json_to_resume(data: dict[str, Any]) -> str:
            sections: list[ResumeSection] = []
            if data.get("summary"):
                sections.append(ResumeSection("Summary", [str(data.get("summary")).strip()]))
            skills = data.get("skills") or []
            if skills:
                sections.append(ResumeSection("Skills", [", ".join([str(s).strip() for s in skills if str(s).strip()])]))
            exp_lines: list[str] = []
            for ex in data.get("experience") or []:
                if not isinstance(ex, dict):
                    continue
                title = str(ex.get("title") or "").strip()
                company = str(ex.get("company") or "").strip()
                start = str(ex.get("start_date") or "").strip()
                end = str(ex.get("end_date") or "").strip()
                header = f"{title} at {company}".strip()
                if start or end:
                    header += f" ({start} - {end})"
                if header.strip():
                    exp_lines.append(header.strip())
                for bullet in ex.get("bullets") or []:
                    bullet_text = str(bullet).strip()
                    if bullet_text:
                        exp_lines.append(f"- {bullet_text}")
            if exp_lines:
                sections.append(ResumeSection("Experience", exp_lines))
            edu_lines: list[str] = []
            for ed in data.get("education") or []:
                if isinstance(ed, dict):
                    degree = str(ed.get("degree") or "").strip()
                    institution = str(ed.get("institution") or "").strip()
                    years = str(ed.get("years") or "").strip()
                    gpa = str(ed.get("gpa") or "").strip()
                    line = ", ".join([x for x in [degree, institution] if x])
                    if years:
                        line += f" ({years})"
                    if gpa:
                        line += f" GPA: {gpa}"
                    if line.strip():
                        edu_lines.append(line.strip())
                else:
                    text = str(ed).strip()
                    if text:
                        edu_lines.append(text)
            if edu_lines:
                sections.append(ResumeSection("Education", edu_lines))
            proj_lines: list[str] = []
            for pr in data.get("projects") or []:
                if not isinstance(pr, dict):
                    continue
                name = str(pr.get("name") or "").strip()
                desc = str(pr.get("description") or "").strip()
                techs = ", ".join([str(t).strip() for t in (pr.get("technologies") or []) if str(t).strip()])
                line = f"{name} – {desc}".strip(" –")
                if techs:
                    line += f" (Technologies: {techs})"
                if line.strip():
                    proj_lines.append(line.strip())
            if proj_lines:
                sections.append(ResumeSection("Projects", proj_lines))
            cert_lines = [str(x).strip() for x in (data.get("certifications") or []) if str(x).strip()]
            if cert_lines:
                sections.append(ResumeSection("Certifications", cert_lines))
            lang_lines = [str(x).strip() for x in (data.get("languages") or []) if str(x).strip()]
            if lang_lines:
                sections.append(ResumeSection("Languages", lang_lines))
            return _assemble_resume(sections)

        def _parse_json_response(text: str) -> dict[str, Any] | None:
            if not text:
                return None
            try:
                start = text.find("{")
                end = text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    return json.loads(text[start:end + 1])
                return json.loads(text)
            except Exception:
                return None

        profile_lines: list[str] = []
        if structured_profile:
            skills_csv = structured_profile.get("skills_csv") or ", ".join(structured_profile.get("skills") or [])
            contact = " | ".join([x for x in [structured_profile.get("email"), structured_profile.get("phone"), structured_profile.get("location")] if x])
            if structured_profile.get("full_name"):
                profile_lines.append(f"Name: {structured_profile.get('full_name')}")
            if contact:
                profile_lines.append(f"Contact: {contact}")
            if structured_profile.get("summary"):
                profile_lines.append(f"Summary: {structured_profile.get('summary')}")
            if skills_csv:
                profile_lines.append(f"Skills: {skills_csv}")
            profile_lines.append("Work Experience:")
            for we in structured_profile.get("work_experience") or []:
                if not isinstance(we, dict):
                    continue
                title = str(we.get("job_title") or we.get("title") or "").strip()
                company = str(we.get("company") or "").strip()
                start = str(we.get("start_date") or we.get("start_year") or "").strip()
                end = str(we.get("end_date") or we.get("end_year") or "").strip()
                profile_lines.append(f"{title} at {company} ({start} - {end})".strip())
                for item in (we.get("achievements") or []) + (we.get("responsibilities") or []):
                    text = str(item).strip()
                    if text:
                        profile_lines.append(f"- {text}")
            profile_lines.append("Education:")
            for ed in structured_profile.get("education") or []:
                if not isinstance(ed, dict):
                    continue
                degree = str(ed.get("degree") or "").strip()
                field = str(ed.get("field_of_study") or "").strip()
                institution = str(ed.get("institution") or "").strip()
                years = f"{ed.get('start_year') or ''}-{ed.get('end_year') or ''}".strip("-")
                gpa = str(ed.get("gpa") or "").strip()
                line = f"{degree} in {field}, {institution}".strip().strip(',')
                if years:
                    line += f" ({years})"
                if gpa:
                    line += f" GPA: {gpa}"
                profile_lines.append(line)
            profile_lines.append("Projects:")
            for pr in structured_profile.get("projects") or []:
                if not isinstance(pr, dict):
                    continue
                name = str(pr.get("name") or "").strip()
                desc = str(pr.get("description") or "").strip()
                techs = ", ".join([str(t).strip() for t in (pr.get("technologies") or []) if str(t).strip()])
                profile_lines.append(f"{name} – {desc} (Technologies: {techs})".strip())
            profile_lines.append("Certifications:")
            for cert in structured_profile.get("certifications") or []:
                if isinstance(cert, dict):
                    profile_lines.append(" | ".join([str(cert.get(k) or "").strip() for k in ["name", "issuing_org", "date_earned"] if str(cert.get(k) or "").strip()]))
            profile_lines.append("Languages:")
            for lang in structured_profile.get("languages") or []:
                if isinstance(lang, dict):
                    name = str(lang.get("name") or "").strip()
                    prof = str(lang.get("proficiency") or "").strip()
                    if name and prof:
                        profile_lines.append(f"{name} ({prof})")

        structured_text = "\n".join(profile_lines).strip()
        prior_hits = _keyword_hits(resume_text, keywords)
        priority_missing = [keyword for keyword in keywords if keyword not in prior_hits][:12]
        key_techs = keywords[:8]

        prompt = f"""
    You are a professional resume writer.
    Return valid JSON only with keys: summary, skills, experience, education, projects, certifications, languages.
    Use only the data below and do not invent facts.

        Key job keywords, tools, and technologies to include where truthful: {", ".join(keywords[:12]) or 'none identified'}
        Priority keywords currently missing from the source resume: {", ".join(priority_missing) or 'none identified'}
        When the job description mentions important tools or technologies, surface them in the summary, skills, and experience bullets if the candidate truly has them.
        Prefer explicit ATS-friendly wording such as the exact skill or technology names from the job description.
        Incorporate at least 3 of the priority missing keywords into the skills list and/or experience bullets where truthful.
        Use exact keyword strings (verbatim) for ATS matching.
        Summary must explicitly mention the target job title ({job_title or 'Not specified'}) and at least 2 key technologies from: {", ".join(key_techs) or 'none identified'}.
        Bullet formatting rules: use clean plain text, one bullet per line, each bullet must begin with '- ' (dash + space), separate bullets with line breaks, and never use literal backslashes or escape sequences.
        Do not output any placeholder text or escaped characters like \\n or \\-.

    Candidate data:
    {structured_text}

    Job title: {job_title or 'Not specified'}
    Job description:
    {job_description[:3000]}

    Rules:
    - skills must be an array of strings.
    - experience must be an array of objects with title, company, start_date, end_date, bullets.
    - bullets must be clean plain text, one bullet per item, no backslashes, no escaped characters.
    - omit empty sections.
    """

        raw = provider.ask("Resume JSON generation", prompt, temperature=0.1)
        data = _parse_json_response(raw or "")
        if isinstance(data, dict):
            return _ensure_priority_keywords(_normalize_resume_format(_json_to_resume(data)), priority_missing, min_count=3)

        plain_prompt = f"""
    You are a professional resume writer. Using the candidate data below, generate a clean one-page ATS-friendly resume tailored for the job: {job_title or 'Not specified'}.
    Use only the real data below. Do not invent facts. Omit empty sections.

    Add these priority missing keywords (verbatim, exact strings) to skills and/or experience bullets where truthful: {", ".join(priority_missing) or 'none identified'}.
    Ensure at least 3 of these priority keywords appear in the final resume.
    Ensure the Summary explicitly references the target role ({job_title or 'Not specified'}) and at least 2 key technologies: {", ".join(key_techs) or 'none identified'}.
    Bullet formatting rules: one bullet per line, start each bullet with '- ' (dash + space), separate bullets with line breaks, and do not use literal backslashes or escape characters such as \\n or \\-.

    Candidate data:
    {structured_text}

    Job description:
    {job_description[:3000]}

    Output only plain text with headings Summary, Skills, Experience, Education, Projects, Certifications, Languages.
    """
        raw2 = provider.ask("Resume text generation", plain_prompt, temperature=0.1)
        cleaned = _clean_text(raw2 or "")
        if cleaned:
            cleaned = _remove_duplicate_paragraphs(cleaned)
            cleaned = _clean_text("\n".join(
                line for line in cleaned.splitlines()
                if not re.search(r"add your|not specified|experience at|add degree|your degree", line, flags=re.IGNORECASE)
            ))
            return _ensure_priority_keywords(_normalize_resume_format(cleaned), priority_missing, min_count=3)
        return None

    polished_resume = _llm_polish_resume(original_resume, job_description, job_keywords, structured_profile=structured_profile, job_title=job_title)
    if isinstance(polished_resume, str) and polished_resume.strip().lower().startswith("ai error:"):
        polished_resume = None
    fixed_resume_text = _normalize_resume_format(polished_resume or original_resume)
    fixed_resume_text = _ensure_priority_keywords(fixed_resume_text, missing_keywords, min_count=3)

    # Ensure summary references the target role and key technologies.
    key_techs = [kw for kw in job_keywords[:8] if kw]
    sections = _parse_sections(fixed_resume_text)
    for section in sections:
        if section.title.lower() == "summary" and section.lines:
            summary_text = " ".join(section.lines).strip()
            additions: list[str] = []
            if job_title and job_title.lower() not in summary_text.lower():
                additions.append(f"Tailored for {job_title}.")
            tech_hits = [kw for kw in key_techs if re.search(rf"\b{re.escape(kw)}\b", summary_text, flags=re.IGNORECASE)]
            if len(tech_hits) < 2 and key_techs:
                needed = [kw for kw in key_techs if kw not in tech_hits][: max(0, 2 - len(tech_hits))]
                if needed:
                    additions.append(f"Core technologies: {', '.join(needed)}.")
            if additions:
                section.lines = [f"{summary_text} {' '.join(additions)}".strip()]
            break
    if sections:
        fixed_resume_text = _assemble_resume(sections)

    final_hits = _keyword_hits(fixed_resume_text, job_keywords)
    final_missing = [keyword for keyword in job_keywords if keyword not in final_hits]
    ats_score = _score_resume(fixed_resume_text, job_description, job_keywords, final_missing)

    changes_made: list[str] = []
    if polished_resume:
        changes_made.append("Regenerated resume from structured data with ATS-focused formatting.")
    if any(re.search(rf"\b{re.escape(k)}\b", fixed_resume_text, flags=re.IGNORECASE) for k in missing_keywords[:6]):
        changes_made.append("Inserted priority missing keywords into skills/experience for stronger ATS matching.")
    if not re.search(r"\\-", fixed_resume_text) and not any(re.match(r"^[-•]\S", line.strip()) for line in fixed_resume_text.splitlines()):
        changes_made.append("Normalized bullet formatting (removed escaped markers and fixed spacing).")

    return {
        "fixed_resume_text": fixed_resume_text,
        "sections": _extract_sections_for_output(fixed_resume_text),
        "ats_score": ats_score,
        "changes_made": changes_made,
    }
