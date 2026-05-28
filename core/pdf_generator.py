"""ATS-Friendly PDF Generation using ReportLab Platypus.

This generator accepts either a plain text resume or a structured `sections` dict
and produces a professionally styled, ATS-friendly PDF.
"""
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    KeepTogether,
    Table,
    TableStyle,
    ListFlowable,
    ListItem,
)
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_RIGHT, TA_LEFT
import os
import re
from typing import Any


def _ensure_styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TitleLarge", parent=styles["Heading1"], fontSize=18, leading=22, spaceAfter=6, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="Heading1Bold", parent=styles["Heading2"], fontSize=14, leading=16, spaceBefore=8, spaceAfter=6, alignment=TA_LEFT))
    styles.add(ParagraphStyle(name="NormalText", parent=styles["Normal"], fontSize=11, leading=14))
    styles.add(ParagraphStyle(name="ContactLine", parent=styles["Normal"], fontSize=10, leading=12, textColor=colors.grey))
    styles.add(ParagraphStyle(name="CustomBullet", parent=styles["Normal"], leftIndent=12, bulletIndent=6, bulletFontSize=8, fontSize=10, leading=13))
    return styles


def _parse_markdown_sections(text: str) -> dict[str, Any]:
    """Very small parser for Markdown-like headings (## Summary, ## Skills, etc.)

    Returns a dict of sections where values are either strings or lists.
    """
    sections: dict[str, Any] = {}
    current = None
    buf: list[str] = []
    for line in text.splitlines():
        h = re.match(r"^#{1,3}\s*(.+)", line)
        if h:
            if current:
                sections[current] = "\n".join(buf).strip()
            current = h.group(1).strip().lower()
            buf = []
            continue
        # Detect all-caps headings
        if line.strip() and line.strip() == line.strip().upper() and len(line.strip()) < 40:
            if current:
                sections[current] = "\n".join(buf).strip()
            current = line.strip().lower()
            buf = []
            continue
        buf.append(line)

    if current:
        sections[current] = "\n".join(buf).strip()
    return sections


def _make_bullets(story, bullets, styles):
    items = []
    for b in bullets:
        text = str(b).strip()
        if not text:
            continue
        items.append(ListItem(Paragraph(text, styles["NormalText"]), leftIndent=6))
    if items:
        story.append(ListFlowable(items, bulletType="bullet", start="-", leftIndent=12))


def generate_resume_pdf(content_or_sections: Any, output_path: str, candidate_name: str | None = None, contact_lines: list[str] | None = None) -> bool:
    """Generate a styled, ATS-friendly PDF.

    - `content_or_sections` may be:
      - a dict with keys: summary, skills, experience (list), education (list), projects, certifications, languages
      - a plain text string (will attempt Markdown parsing)
    - `candidate_name` and `contact_lines` are optional metadata used at the top of the PDF.
    """
    try:
        doc = SimpleDocTemplate(
            output_path,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=36,
        )

        styles = _ensure_styles()
        story: list[Any] = []

        # Header: Candidate name
        if not candidate_name:
            candidate_name = ""
        if candidate_name:
            story.append(Paragraph(candidate_name, styles["TitleLarge"]))

        # Contact lines
        if contact_lines:
            contact_text = "  ".join(contact_lines)
            story.append(Paragraph(contact_text, styles["ContactLine"]))
            story.append(Spacer(1, 0.12 * inch))

        # Normalize sections
        sections = {}
        if isinstance(content_or_sections, dict):
            sections = content_or_sections
        elif isinstance(content_or_sections, str):
            sections = _parse_markdown_sections(content_or_sections)
        else:
            # try to coerce
            sections = {}

        # Order of sections to render
        order = ["summary", "skills", "experience", "education", "projects", "certifications", "languages"]

        for key in order:
            value = sections.get(key) or sections.get(key.capitalize()) or sections.get(key.upper())
            if not value:
                continue

            # Section heading
            story.append(Paragraph(key.capitalize(), styles["Heading1Bold"]))

            # Render content depending on type
            if key == "skills":
                # skills may be list or comma separated
                skills_list = []
                if isinstance(value, list):
                    skills_list = value
                elif isinstance(value, str):
                    # split by comma or newline
                    if "," in value:
                        skills_list = [s.strip() for s in value.split(",") if s.strip()]
                    else:
                        skills_list = [s.strip() for s in value.splitlines() if s.strip()]
                if skills_list:
                    skill_line = ", ".join(skills_list)
                    story.append(Paragraph(skill_line, styles["NormalText"]))

            elif key == "summary":
                if isinstance(value, list):
                    for p in value:
                        if p:
                            story.append(Paragraph(str(p), styles["NormalText"]))
                else:
                    for para in str(value).splitlines():
                        if para.strip():
                            story.append(Paragraph(para.strip(), styles["NormalText"]))

            elif key == "experience":
                # Expecting a list of dicts with title, organization, year, bullets
                if isinstance(value, list):
                    for item in value:
                        title = item.get("title") or ""
                        org = item.get("organization") or ""
                        year = item.get("year") or ""
                        bullets = item.get("bullets") or []

                        left = f"<b>{title}</b>"
                        if org:
                            left += f" — {org}"

                        # Table with left (title+org) and right (year)
                        tbl = Table([[Paragraph(left, styles["NormalText"]), Paragraph(str(year), ParagraphStyle(name="Right", parent=styles["NormalText"], alignment=TA_RIGHT))]], colWidths=[4.8*inch, 1.4*inch])
                        tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("ALIGN", (1, 0), (1, 0), "RIGHT")]))
                        block = [tbl]
                        # Bullets
                        if bullets:
                            _make_bullets(block, bullets, styles)

                        story.append(KeepTogether(block))

            elif key in ("education", "projects", "certifications"):
                if isinstance(value, list):
                    for item in value:
                        title = item.get("title") or item.get("name") or ""
                        org = item.get("organization") or item.get("institution") or ""
                        year = item.get("year") or ""
                        bullets = item.get("bullets") or []

                        left = f"<b>{title}</b>"
                        if org:
                            left += f" — {org}"

                        tbl = Table([[Paragraph(left, styles["NormalText"]), Paragraph(str(year), ParagraphStyle(name="Right", parent=styles["NormalText"], alignment=TA_RIGHT))]], colWidths=[4.8*inch, 1.4*inch])
                        tbl.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
                        block = [tbl]
                        if bullets:
                            _make_bullets(block, bullets, styles)
                        story.append(KeepTogether(block))

            elif key == "languages":
                if isinstance(value, list):
                    lang_line = ", ".join(value)
                    story.append(Paragraph(lang_line, styles["NormalText"]))
                elif isinstance(value, str):
                    story.append(Paragraph(value.strip(), styles["NormalText"]))

            else:
                # Generic rendering
                if isinstance(value, list):
                    for v in value:
                        if v:
                            story.append(Paragraph(str(v), styles["NormalText"]))
                else:
                    for para in str(value).splitlines():
                        if para.strip():
                            story.append(Paragraph(para.strip(), styles["NormalText"]))

            story.append(Spacer(1, 0.12 * inch))

        doc.build(story)
        return True
    except Exception as e:
        print(f"PDF generation error: {e}")
        return False
