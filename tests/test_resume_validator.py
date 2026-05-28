from core.resume_validator import validate_resume_output


def test_validate_resume_output_does_not_flag_chart_words_in_text():
    resume_text = "Summary\nBuilt dashboards and presented charts to stakeholders.\nSkills\nPython, SQL\nExperience\n- Delivered reporting improvements.\nEducation\nBS Computer Science\nProjects\n- Analytics dashboard"
    html_resume = "<html><body><div>Built dashboards and presented charts to stakeholders.</div></body></html>"

    result = validate_resume_output(resume_text, html_resume, job_description="")

    assert "graphics" not in " ".join(result["warnings"]).lower()
    assert "Forbidden layout elements detected: graphics" not in result["message"]


def test_validate_resume_output_treats_density_as_suggestion():
    resume_text = "Summary\nPython Python Python Python SQL SQL SQL\nSkills\nPython, SQL, React\nExperience\n- Built Python services\nEducation\nBS Computer Science\nProjects\n- Python project"
    html_resume = "<html><body><main><section>Python content</section></main></body></html>"

    result = validate_resume_output(resume_text, html_resume, job_description="")

    assert result["passed"] is True
    assert result["warnings"] == []
    assert result["suggestions"]
    assert "Consider reducing repetition of keywords" in result["message"]
