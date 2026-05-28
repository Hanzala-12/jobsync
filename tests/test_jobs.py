from __future__ import annotations

import json

from backend.models import Job, User, UserProfile
from core.normalizer import normalize_job


def _create_user(test_db, email: str = "jobs@example.com"):
    user = User(email=email, hashed_password="hashed", name="Jobs User", is_active=True, token_version=0)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def test_normalize_job_standardizes_city_and_type():
    normalized = normalize_job(
        {
            "title": "Senior Backend Engineer",
            "company": "Careem",
            "city": "KHI",
            "location": "KHI",
            "description": "Build APIs in FastAPI",
            "apply_url": "https://example.com/apply",
            "salary": "250000 - 350000",
            "job_type": "remote",
            "posted_date": "Today",
        },
        "adzuna",
    )

    assert normalized["city"] == "karachi"
    assert normalized["location"] == "karachi"
    assert normalized["job_type"] == "remote"
    assert normalized["salary"] == "PKR 250000 - 350000"
    assert normalized["source"] == "adzuna"


def test_job_match_endpoint_returns_skill_overlap(test_client, test_db, auth_headers):
    user = _create_user(test_db, "match@example.com")
    headers = auth_headers(user)

    profile = UserProfile(
        user_id=user.id,
        resume_text="Backend engineer with Python, FastAPI, SQL, and Docker experience.",
        full_name="Match User",
        email="match@example.com",
        skills=["Python", "FastAPI", "SQL", "Docker"],
        achievements=[],
        preferred_job_titles=["Backend Engineer"],
        desired_salary_min=0,
        desired_salary_max=0,
        willing_to_relocate=False,
        preferred_work_location="remote",
        summary="Backend engineer",
        location="Karachi",
    )
    job = Job(
        title="Backend Engineer",
        company="Acme",
        location="Remote",
        city="Remote",
        description="We need Python, FastAPI, SQL, and Docker for our backend platform.",
        url="https://example.com/job",
        source="manual",
        external_id="job-1",
    )
    test_db.add(profile)
    test_db.add(job)
    test_db.commit()
    test_db.refresh(job)

    response = test_client.get(f"/jobs/{job.id}/match", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == job.id
    assert data["match_percentage"] > 0
    assert "Python" in data["matched_skills"]
    assert "Skills matched" in data["explanation"]


def test_job_upsert_creates_row(test_client):
    response = test_client.post(
        "/jobs/upsert",
        json={
            "title": "Data Analyst",
            "company": "Insight Loop",
            "description": "Analyze SQL dashboards and reporting",
            "url": "https://example.com/data-analyst",
            "source": "manual",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Data Analyst"
    assert data["company"] == "Insight Loop"
    assert data["source"] == "manual"
    assert data["url"] == "https://example.com/data-analyst"
