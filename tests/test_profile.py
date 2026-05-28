from __future__ import annotations

from backend.models import Job, User, UserProfile
import backend.routers.profile as profile_router


def _create_user(test_db, email: str = "profile@example.com"):
    user = User(email=email, hashed_password="hashed", name="Profile User", is_active=True, token_version=0)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def test_profile_crud_and_selection_flow(test_client, test_db, auth_headers):
    user = _create_user(test_db, "profile-crud@example.com")
    headers = auth_headers(user)
    test_db.close()

    create_response = test_client.post(
        "/profile",
        json={
            "full_name": "Jane Developer",
            "email": "jane@example.com",
            "phone": "+92 300 1234567",
            "location": "Karachi",
            "summary": "Backend engineer",
            "skills": ["Python", "FastAPI", "SQL"],
            "achievements": ["Shipped APIs"],
            "preferred_job_titles": ["Backend Engineer"],
            "desired_salary_min": 150000,
            "desired_salary_max": 250000,
            "willing_to_relocate": True,
            "preferred_work_location": "remote",
            "resume_text": "Resume text: Backend engineer with FastAPI",
            "education": [{"degree": "BS CS", "institution": "Test University", "start_year": 2018, "end_year": 2022}],
            "work_experience": [{"job_title": "Backend Engineer", "company": "Acme", "responsibilities": ["Build APIs"], "achievements": ["Improved latency"]}],
            "certifications": [{"name": "AWS Certified", "issuing_org": "AWS"}],
            "projects": [{"name": "Dashboard", "description": "Built dashboard", "technologies": ["React", "Python"]}],
            "languages": [{"name": "English", "proficiency": "Fluent"}],
        },
        headers=headers,
    )
    assert create_response.status_code == 200
    profile = create_response.json()["profile"]
    assert profile["full_name"] == "Jane Developer"
    assert profile["skills"] == ["Python", "FastAPI", "SQL"]
    assert profile["desired_salary_min"] == 150000

    profile_id = profile["id"]
    list_response = test_client.get("/profile", headers=headers)
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["exists"] is True

    select_response = test_client.post(f"/profile/select/{profile_id}", headers=headers)
    assert select_response.status_code == 200
    assert select_response.json()["selected_profile_id"] == profile_id

    list_response = test_client.get("/profile", headers=headers)
    assert list_response.status_code == 200
    list_data = list_response.json()
    assert list_data["selected_profile_id"] == profile_id

    selected_response = test_client.get("/profile/selected", headers=headers)
    assert selected_response.status_code == 200
    assert selected_response.json()["selected_profile_id"] == profile_id

    get_response = test_client.get(f"/profile/{profile_id}", headers=headers)
    assert get_response.status_code == 200
    assert get_response.json()["profile_completeness"] >= 50

    delete_response = test_client.delete(f"/profile/{profile_id}", headers=headers)
    assert delete_response.status_code == 200
    assert delete_response.json()["status"] == "success"


def test_build_resume_uses_structured_profile_and_soft_warning(test_client, test_db, auth_headers, monkeypatch):
    user = _create_user(test_db, "resume@example.com")
    headers = auth_headers(user)

    profile = UserProfile(
        user_id=user.id,
        resume_text="Backend engineer resume text",
        full_name="Jane Developer",
        email="jane@example.com",
        phone="+92 300 1234567",
        location="Karachi",
        summary="Backend engineer",
        skills=["Python", "FastAPI", "SQL"],
        achievements=["Shipped APIs"],
        preferred_job_titles=["Backend Engineer"],
        desired_salary_min=0,
        desired_salary_max=0,
        willing_to_relocate=False,
        preferred_work_location="remote",
    )
    job = Job(
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        city="Remote",
        description="Build Python APIs with FastAPI and SQL",
        url="https://example.com/job",
        source="manual",
        external_id="resume-job-1",
    )
    test_db.add(profile)
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)
    test_db.close()

    monkeypatch.setattr(
        profile_router,
        "analyze_and_fix_resume",
        lambda *args, **kwargs: {
            "fixed_resume_text": "Summary\nJane Developer\nExperience\n- Built APIs",
            "ats_score": 88,
            "changes_made": ["Added skills"],
            "sections": {
                "summary": ["Backend engineer"],
                "skills": ["Python", "FastAPI", "SQL"],
                "achievements": ["Shipped APIs"],
            },
        },
    )
    monkeypatch.setattr(profile_router, "render_resume_html", lambda payload: f"<html>{payload['validation_message']}</html>")
    monkeypatch.setattr(
        profile_router,
        "validate_resume_output",
        lambda *args, **kwargs: {
            "passed": True,
            "warnings": [],
            "suggestions": ["Consider reducing repetition of keywords; the resume reads a bit dense."],
            "message": "Consider reducing repetition of keywords; the resume reads a bit dense.",
            "keyword_density": 0.31,
        },
    )
    monkeypatch.setattr(profile_router, "save_resume_artifacts", lambda *args, **kwargs: {"text_path": "x", "html_path": "y"})

    response = test_client.post(f"/build_resume/{job.id}", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["validation_passed"] is True
    assert data["validation_message"] == "Consider reducing repetition of keywords; the resume reads a bit dense."
    assert data["ats_score"] == 88
    assert "Built APIs" in data["fixed_resume_text"]
