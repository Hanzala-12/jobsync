#!/usr/bin/env python3
"""Simple integration test for the hybrid resume pipeline.

This script simulates LLM section output, fills the canonical blueprint,
and generates a PDF to validate the end-to-end flow.
"""
import os
import sys

from core.resume_blueprint_engine import ResumeBlueprintEngine
from core.pdf_generator import generate_resume_pdf
from core.resume_analyzer import _extract_sections_for_output


def main() -> int:
    engine = ResumeBlueprintEngine()
    blueprint = engine.load_blueprint()

    # Simulated LLM output (deterministic for testing)
    sample_llm_sections = {
        "contact": {
            "full_name": "Jane Developer",
            "job_title": "Backend Engineer",
            "email": "jane@example.com",
            "phone": "+1-555-0100",
            "location": "Remote, USA",
            "linkedin_url": "https://linkedin.com/in/janedev",
            "portfolio_url": "https://janedev.example.com",
        },
        "summary": "Backend Engineer with 6+ years building scalable APIs and data pipelines. Proven in Python, SQL, and AWS.",
        "skills": ["Python", "FastAPI", "Postgres", "AWS", "Docker", "Kubernetes"],
        "experience": [
            {
                "job_title": "Senior Backend Engineer",
                "company": "TechCo",
                "start_date": "2019-01",
                "end_date": "2023-06",
                "bullets": [
                    "- Designed and implemented a microservice architecture that reduced latency by 40%",
                    "- Built automated ETL pipelines processing 10M+ records/day",
                ],
            }
        ],
        "education": [
            {"degree": "B.S. Computer Science", "institution": "State University", "years": "2012 - 2016", "gpa": "3.7"}
        ],
        "projects": [
            {"name": "Job Match Engine", "description": "Engine for matching candidates to jobs", "technologies": ["Python", "Postgres"]}
        ],
    }

    filled = engine.fill_blueprint(blueprint, sample_llm_sections)
    assert "Contact Information" in filled
    assert "Professional Summary" in filled
    assert "Skills" in filled

    # Convert to structured sections for the PDF generator
    print('DEBUG: filled resume text:\n')
    print(filled)
    sections = _extract_sections_for_output(filled)
    print('\nDEBUG: extracted sections:')
    import json
    print(json.dumps(sections, indent=2))

    out_dir = os.path.join(os.getcwd(), "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_pdf = os.path.join(out_dir, "hybrid_resume_test.pdf")

    # Coerce parsed sections into the dict format expected by generate_resume_pdf
    pdf_sections = {}
    pdf_sections["summary"] = sections.get("summary", "")
    pdf_sections["skills"] = sections.get("skills", [])
    pdf_sections["experience"] = sections.get("experience", [])
    # Convert education/project lines (strings) into list of dicts with name/title keys
    edu_lines = sections.get("education", []) or []
    pdf_sections["education"] = [ {"name": line} if isinstance(line, str) else line for line in edu_lines ]
    proj_lines = sections.get("projects", []) or []
    pdf_sections["projects"] = [ {"name": line} if isinstance(line, str) else line for line in proj_lines ]

    ok = generate_resume_pdf(pdf_sections, out_pdf, candidate_name=sample_llm_sections["contact"]["full_name"], contact_lines=[sample_llm_sections["contact"]["email"], sample_llm_sections["contact"]["phone"]])
    if not ok or not os.path.exists(out_pdf):
        print("PDF generation failed")
        return 2

    # Basic assertions on sections
    for key in ("summary", "skills", "experience", "education"):
        if key not in sections or not sections[key]:
            print(f"FAIL: missing or empty section {key}")
            return 3

    print("PASS: Hybrid resume pipeline produced a PDF at", out_pdf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
