import sys, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.resume_analyzer import analyze_and_fix_resume
resume_text='''Jane Developer | Karachi
Contact: jane.dev@example.com | 555-0100 | https://linkedin.example/jane
Summary: Tailored for Backend Engineer at TestCo.
Skills: Python, SQL, React, FastAPI
Education:
- BS Computer Science | Test University | 2016-2020
Experience:
- Backend Engineer | TestCo | 2021-01 to 2023-06
- Responsibility: Built REST APIs
- Responsibility: Owned data pipelines
- Achievement: Reduced API latency by 30%
- Achievement: Implemented CI/CD
Projects:
- Analytics Dashboard | Built dashboard for analytics | Technologies: React, Python
Certifications:
- AWS Certified Developer | AWS | 2022-05
Languages:
- English | Professional
Achievements:
- Led backend migration
- Mentored junior devs'''
job_description='Build REST APIs, data pipelines, dashboards; use Python, FastAPI, SQL; work with stakeholders.'
res = analyze_and_fix_resume(resume_text, job_description)
sections = res.get('sections')
out = Path(__file__).resolve().parents[1] / 'outputs' / 'analyzer_sections.json'
out.parent.mkdir(parents=True, exist_ok=True)
with open(out, 'w', encoding='utf-8') as f:
    json.dump(sections, f, indent=2)
print('Wrote', out)
