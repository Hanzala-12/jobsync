"""Resume Blueprint Engine

Provides loading and rendering of a canonical resume blueprint to plain-text
or simple structured output suitable for PDF generation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


class ResumeBlueprintEngine:
    def __init__(self, blueprint_path: Optional[str] = None):
        self.blueprint_path = blueprint_path
        self._blueprint: Optional[Dict[str, Any]] = None

    def load_blueprint(self, path: Optional[str] = None) -> Dict[str, Any]:
        p = Path(path) if path else Path(__file__).resolve().parents[1] / "blueprints" / "resume_blueprint.json"
        if not p.exists():
            raise FileNotFoundError(f"Resume blueprint not found at {p}")
        with p.open("r", encoding="utf-8") as fh:
            self._blueprint = json.load(fh)
        return self._blueprint

    def fill_blueprint(self, blueprint: Dict[str, Any], llm_sections: Optional[Dict[str, Any]] = None, structured_profile: Optional[Dict[str, Any]] = None) -> str:
        """Render the blueprint using `llm_sections` (preferred) or `structured_profile`.

        Returns a plain-text resume string with section headings and content ready
        for the PDF generator.
        """
        sections_cfg = sorted(blueprint.get("sections", []), key=lambda s: s.get("order", 0))
        parts: List[str] = []

        for sec in sections_cfg:
            name = sec.get("name")
            title = sec.get("title") or (name or "").title()
            parts.append(title)

            # Determine source value
            value = None
            if llm_sections and name in llm_sections:
                value = llm_sections.get(name)
            elif structured_profile and name in structured_profile:
                value = structured_profile.get(name)

            content_lines: List[str] = []

            if name == "contact":
                contact = value if isinstance(value, dict) else {}
                if not contact and structured_profile:
                    contact = {
                        "full_name": structured_profile.get("full_name") or "",
                        "job_title": structured_profile.get("job_title") or "",
                        "email": structured_profile.get("email") or "",
                        "phone": structured_profile.get("phone") or "",
                        "location": structured_profile.get("location") or "",
                        "linkedin_url": structured_profile.get("linkedin_url") or "",
                        "portfolio_url": structured_profile.get("portfolio_url") or "",
                    }
                name_line = " | ".join([p for p in [contact.get("full_name") or "", contact.get("job_title") or ""] if p])
                if name_line:
                    content_lines.append(name_line)
                contact_line = " | ".join([p for p in [contact.get("email") or "", contact.get("phone") or "", contact.get("location") or "", contact.get("linkedin_url") or "", contact.get("portfolio_url") or ""] if p])
                if contact_line:
                    content_lines.append(contact_line)

            elif name == "summary":
                summary = value if isinstance(value, str) else (structured_profile.get("summary") if structured_profile else "")
                if summary:
                    content_lines.append(str(summary).strip())

            elif name == "skills":
                skills_list: List[str] = []
                if isinstance(value, list):
                    skills_list = [str(s).strip() for s in value if s]
                elif isinstance(value, str):
                    if "," in value:
                        skills_list = [s.strip() for s in value.split(",") if s.strip()]
                    else:
                        skills_list = [s.strip() for s in value.splitlines() if s.strip()]
                elif structured_profile:
                    skills_list = [s.strip() for s in (structured_profile.get("skills") or []) if s]
                if skills_list:
                    content_lines.append(", ".join(skills_list))

            elif name == "experience":
                exp_items = value if isinstance(value, list) else (structured_profile.get("work_experience") if structured_profile else [])
                for item in exp_items or []:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("job_title") or item.get("title") or ""
                    company = item.get("company") or ""
                    start = item.get("start_date") or item.get("start_year") or ""
                    end = item.get("end_date") or item.get("end_year") or ""
                    dates = " - ".join([p for p in [str(start).strip(), str(end).strip()] if p]).strip()
                    header = " | ".join([p for p in [title, company, dates] if p])
                    if header:
                        content_lines.append(header)
                    bullets = item.get("bullets") or item.get("achievements") or item.get("responsibilities") or []
                    for b in bullets or []:
                        if b and isinstance(b, str) and b.strip():
                            content_lines.append(f"- {b.strip()}")

            elif name == "education":
                edu_items = value if isinstance(value, list) else (structured_profile.get("education") if structured_profile else [])
                for item in edu_items or []:
                    if not isinstance(item, dict):
                        continue
                    degree = item.get("degree") or ""
                    institution = item.get("institution") or ""
                    years = item.get("years") or " ".join([str(item.get("start_year") or ""), str(item.get("end_year") or "")]).strip()
                    header = " | ".join([p for p in [degree, institution, years] if p])
                    if header:
                        content_lines.append(header)
                    gpa = item.get("gpa") or ""
                    if gpa:
                        content_lines.append(f"GPA: {gpa}")

            elif name == "projects":
                proj_items = value if isinstance(value, list) else (structured_profile.get("projects") if structured_profile else [])
                for item in proj_items or []:
                    if not isinstance(item, dict):
                        continue
                    namep = item.get("name") or item.get("title") or ""
                    desc = item.get("description") or ""
                    tech = item.get("technologies") or ""
                    header = " | ".join([p for p in [namep, desc] if p])
                    if header:
                        content_lines.append(header)
                    if tech:
                        if isinstance(tech, list):
                            tech_line = ", ".join([str(t).strip() for t in tech if t])
                        else:
                            tech_line = str(tech)
                        content_lines.append(f"Technologies: {tech_line}")

            else:
                # Generic section rendering
                if isinstance(value, list):
                    for v in value:
                        if isinstance(v, dict):
                            line = " | ".join([str(v.get(k) or "").strip() for k in v.keys() if v.get(k)])
                            if line:
                                content_lines.append(line)
                        elif isinstance(v, str) and v.strip():
                            content_lines.append(v.strip())
                elif isinstance(value, str) and value.strip():
                    content_lines.append(value.strip())

            if content_lines:
                parts.append("\n".join(content_lines))
            else:
                parts.append("")

        # Join sections with double newlines
        return "\n\n".join([p for p in parts])
