from core.resume_analyzer import analyze_and_fix_resume


def test_resume_tailoring_generates_content():
    profile = {
        "full_name": "Jane Developer",
        "email": "jane@example.com",
        "skills": ["Python", "SQL", "React", "FastAPI"],
        "work_experience": [
            {"job_title": "Backend Engineer", "company": "TestCo", "start_date": "2021", "end_date": "2023", "achievements": ["Built REST APIs", "Improved performance by 30%"]}
        ],
        "education": [{"degree": "BS Computer Science", "institution": "Test University", "start_year": "2016", "end_year": "2020"}],
        "projects": [{"name": "Analytics Dashboard", "technologies": ["React", "Python"], "description": "Built dashboard for analytics."}],
    }

    job_description = "We need a Backend Engineer experienced with Python, FastAPI, SQL and building data pipelines and dashboards."

    result = analyze_and_fix_resume(profile.get("resume_text") or "Summary\nExperienced backend engineer.", job_description, structured_profile=profile, job_title="Backend Engineer")

    text = result.get("fixed_resume_text", "")
    sections = result.get("sections", {})

    assert len(sections.get("skills", [])) >= 3, "Expected at least 3 skills"
    experience_secs = sections.get("experience", [])
    assert any(len(item.get("bullets", [])) > 0 for item in experience_secs), "Expected experience bullets"
    forbidden = ["add your degree", "placeholder", "not specified"]
    assert all(kw not in text.lower() for kw in forbidden), "Found placeholder phrases in resume"
