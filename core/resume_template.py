from __future__ import annotations

from html import escape
from typing import Any, Iterable, Mapping

from core.resume_standards import ATS_FRIENDLY_FONTS, RESUME_STANDARD_HEADINGS


def _normalize_lines(values: Iterable[str] | None) -> list[str]:
    items: list[str] = []
    for value in values or []:
        text = str(value or "").strip()
        if text:
            items.append(text)
    return items


def _render_list(items: Iterable[str], class_name: str) -> str:
    normalized = _normalize_lines(items)
    if not normalized:
        return '<div class="resume-empty">Not provided</div>'
    return "".join(f'<span class="resume-pill {class_name}">{escape(item)}</span>' for item in normalized)


def _render_block(items: Iterable[Mapping[str, Any]] | Iterable[str], empty_message: str) -> str:
    rendered: list[str] = []
    normalized = list(items or [])
    if not normalized:
        return f'<div class="resume-empty">{escape(empty_message)}</div>'

    for item in normalized:
        if isinstance(item, Mapping):
            title = escape(str(item.get("title") or item.get("role") or item.get("name") or item.get("job_title") or ""))
            org = escape(str(item.get("organization") or item.get("company") or item.get("institution") or ""))
            # Accept multiple possible keys for bullet/details lists
            details = _normalize_lines(item.get("bullets") or item.get("details") or item.get("responsibilities") or item.get("achievements") or [])
            year = escape(str(item.get("year") or item.get("date") or ""))
            header = " • ".join(part for part in [title, org, year] if part)
            bullet_html = "".join(f"<li>{escape(bullet)}</li>" for bullet in details)
            rendered.append(
                f'<article class="resume-item"><div class="resume-item-title">{header or "Item"}</div>'
                f'{f"<ul>{bullet_html}</ul>" if bullet_html else ""}</article>'
            )
        else:
            rendered.append(f'<div class="resume-line">{escape(str(item))}</div>')
    return "".join(rendered)


def render_resume_html(resume: Mapping[str, Any]) -> str:
    contact_lines = _normalize_lines(resume.get("contact_lines") or [])
    skills = _normalize_lines(resume.get("skills") or [])
    summary = str(resume.get("summary") or "").strip()
    experience = list(resume.get("experience") or [])
    education = list(resume.get("education") or [])
    projects = list(resume.get("projects") or [])
    certifications = list(resume.get("certifications") or [])
    languages = list(resume.get("languages") or [])
    achievements = _normalize_lines(resume.get("achievements") or [])
    validation_message = str(resume.get("validation_message") or "").strip()
    ats_score = int(round(float(resume.get("ats_score") or 0)))
    candidate_name = str(resume.get("candidate_name") or "Tailored Resume").strip()
    tagline = str(resume.get("tagline") or "ATS-friendly, single-column resume format").strip()
    font_stack = ", ".join(ATS_FRIENDLY_FONTS[:2])

    contact_html = ""
    if contact_lines:
        contact_html = "<div class=\"resume-contact\">" + "<span>•</span>".join(f"<span>{escape(line)}</span>" for line in contact_lines) + "</div>"

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>{escape(candidate_name)} - Resume</title>
  <style>
    :root {{
      --resume-text: #101828;
      --resume-muted: #475467;
      --resume-border: #d0d5dd;
      --resume-accent: #0f766e;
      --resume-bg: #ffffff;
      --resume-soft: #f8fafc;
    }}
    * {{ box-sizing: border-box; }}
    html, body {{ margin: 0; padding: 0; background: #e5e7eb; color: var(--resume-text); }}
    body {{ font-family: {font_stack}; line-height: 1.5; }}
    .resume-shell {{ max-width: 860px; margin: 0 auto; padding: 24px; }}
    .resume-page {{ background: var(--resume-bg); border: 1px solid var(--resume-border); border-radius: 16px; padding: 32px; box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08); }}
    .resume-header {{ display: flex; flex-direction: column; gap: 10px; padding-bottom: 18px; border-bottom: 1px solid var(--resume-border); margin-bottom: 22px; }}
    .resume-name {{ font-size: 28px; line-height: 1.1; font-weight: 700; letter-spacing: -0.02em; }}
    .resume-tagline {{ font-size: 13px; color: var(--resume-muted); }}
    .resume-contact {{ display: flex; flex-wrap: wrap; gap: 10px; font-size: 12px; color: var(--resume-muted); }}
    .resume-contact span {{ white-space: nowrap; }}
    .resume-score {{ align-self: flex-start; padding: 6px 10px; border-radius: 999px; background: #ecfdf3; color: #027a48; font-size: 12px; font-weight: 700; }}
    .resume-notice {{ margin: 0 0 18px; padding: 12px 14px; background: var(--resume-soft); border: 1px solid var(--resume-border); border-radius: 12px; color: var(--resume-muted); font-size: 12px; }}
    .resume-section {{ margin-bottom: 20px; }}
    .resume-section h2 {{ margin: 0 0 10px; font-size: 15px; text-transform: none; letter-spacing: 0; padding-bottom: 6px; border-bottom: 1px solid var(--resume-border); }}
    .resume-summary {{ font-size: 13px; color: var(--resume-text); }}
    .resume-skill-list {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .resume-pill {{ display: inline-flex; align-items: center; padding: 6px 10px; border-radius: 999px; background: #eef2ff; color: #1d4ed8; font-size: 12px; font-weight: 600; }}
    .resume-item {{ margin-bottom: 14px; }}
    .resume-item-title {{ font-weight: 700; font-size: 13px; margin-bottom: 4px; }}
    .resume-item ul {{ margin: 6px 0 0 18px; padding: 0; font-size: 13px; color: var(--resume-text); }}
    .resume-item li {{ margin-bottom: 6px; }}
    .resume-line {{ font-size: 13px; margin-bottom: 8px; }}
    .resume-empty {{ font-size: 13px; color: var(--resume-muted); font-style: italic; }}
    .resume-download {{ appearance: none; border: 0; background: var(--resume-accent); color: white; font: inherit; font-weight: 700; padding: 10px 14px; border-radius: 10px; cursor: pointer; margin-bottom: 18px; }}
    .resume-download:hover {{ filter: brightness(0.95); }}
    .resume-footer {{ margin-top: 18px; color: var(--resume-muted); font-size: 11px; }}
    @media (max-width: 720px) {{
      .resume-shell {{ padding: 12px; }}
      .resume-page {{ padding: 20px; border-radius: 12px; }}
      .resume-name {{ font-size: 24px; }}
    }}
    @media print {{
      body {{ background: white; }}
      .resume-shell {{ padding: 0; }}
      .resume-page {{ box-shadow: none; border: 0; border-radius: 0; }}
      .resume-download, .resume-footer {{ display: none !important; }}
    }}
  </style>
  <script>
    function downloadResumePdf() {{
      if (!window.html2pdf) {{
        alert('PDF export is not loaded yet.');
        return;
      }}
      var element = document.getElementById('resume-export-root');
      if (!element) return;
      var opt = {{
        margin: 0.5,
        filename: 'tailored_resume.pdf',
        image: {{ type: 'jpeg', quality: 0.98 }},
        html2canvas: {{ scale: 2 }},
        jsPDF: {{ unit: 'in', format: 'a4', orientation: 'portrait' }}
      }};
      window.html2pdf().from(element).set(opt).save();
    }}
  </script>
</head>
<body>
  <div class=\"resume-shell\">
    <div class=\"resume-page\" id=\"resume-export-root\">
      <button class=\"resume-download\" type=\"button\" onclick=\"downloadResumePdf()\">Download PDF</button>
      <div class="resume-header">
        <div class=\"resume-name\">{escape(candidate_name)}</div>
        <div class=\"resume-tagline\">{escape(tagline)}</div>
        {contact_html}
        <div class=\"resume-score\">ATS Match Score: {ats_score}%</div>
      </div>
      {f'<div class="resume-notice">{escape(validation_message)}</div>' if validation_message else ''}
      <section class=\"resume-section\">
        <h2>Summary</h2>
        <div class=\"resume-summary\">{escape(summary) if summary else 'Professional summary not provided.'}</div>
      </section>
      <section class=\"resume-section\">
        <h2>Skills</h2>
        <div class=\"resume-skill-list\">{_render_list(skills, 'skill')}</div>
      </section>
      <section class=\"resume-section\">
        <h2>{RESUME_STANDARD_HEADINGS[0]}</h2>
        {_render_block(experience, 'Experience not provided.')}
      </section>
      <section class=\"resume-section\">
        <h2>{RESUME_STANDARD_HEADINGS[2]}</h2>
        {_render_block(education, 'Education not provided.')}
      </section>
      <section class=\"resume-section\">
        <h2>{RESUME_STANDARD_HEADINGS[3]}</h2>
        {_render_block(projects, 'Projects not provided.')}
      </section>
        <section class="resume-section">
          <h2>Certifications</h2>
          {_render_block(certifications, 'Certifications not provided.')}
        </section>
        <section class="resume-section">
          <h2>Languages</h2>
          {_render_block(languages, 'Languages not provided.')}
        </section>
        <section class="resume-section">
          <h2>Achievements</h2>
          {_render_list(achievements, 'achievement')}
        </section>
        <div class=\"resume-footer\">ATS-friendly single-column layout designed for clean parsing and print output.</div>
    </div>
  </div>
</body>
</html>"""
