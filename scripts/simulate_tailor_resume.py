import sys
from pathlib import Path
# Ensure project root is on sys.path so imports like `core.*` resolve
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.resume_analyzer import analyze_and_fix_resume
from core.resume_template import render_resume_html
from core.resume_validator import validate_resume_output

job_description = """We are hiring a Software Engineer to build REST APIs, data pipelines, and dashboards. Experience with Python, SQL, cloud (AWS/GCP), and working with stakeholders is required."""

source_resume_text = """Summary
Experienced backend engineer with strong Python and SQL skills.

Skills
Python, SQL, AWS

Experience
- Built REST APIs and data pipelines
- Delivered dashboards and reporting to stakeholders

Education
BS Computer Science

Projects
- Analytics dashboard project"""

analyzed = analyze_and_fix_resume(source_resume_text, job_description)
fixed = analyzed.get('fixed_resume_text') or source_resume_text
html = render_resume_html({
    "candidate_name": "Simulated Candidate",
    "tagline": "Tailored for Software Engineer",
    "contact_lines": ["sim@example.com"],
    "summary": "",
    "skills": ["Python", "SQL"],
    "experience": [],
    "education": [],
    "projects": [],
    "certifications": [],
    "languages": [],
    "achievements": [],
    "ats_score": int(analyzed.get('ats_score') or 0),
    "validation_message": "",
})

validation = validate_resume_output(fixed, html, job_description)

print('ATS score (analyzer):', analyzed.get('ats_score'))
print('Validation passed:', validation.get('passed'))
print('Validation message:', validation.get('message'))
print('Warnings:', validation.get('warnings'))
print('HTML has export root id:', 'resume-export-root' in html)
print('\n--- HTML snippet ---\n')
print(html[:1000])

# Save example HTML output
out_path = Path(__file__).resolve().parents[1] / 'outputs' / 'example_tailored_resume.html'
out_path.parent.mkdir(parents=True, exist_ok=True)
with open(out_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"Saved example HTML to {out_path}")
