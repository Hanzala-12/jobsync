from __future__ import annotations

import os
import time
from typing import Any
from pathlib import Path
import sys

from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app

CLIENT = TestClient(app)


def _json_or_fail(response) -> dict[str, Any]:
    try:
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}") from exc
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response payload: {data!r}")
    return data


def main() -> int:
    client = CLIENT
    timestamp = int(time.time() * 1000)
    email = f"profile.smoke.{timestamp}@example.com"
    password = "Testpass123!"

    signup = client.post(
        "/auth/signup",
        json={"email": email, "password": password, "name": "Profile Smoke"},
    )
    if signup.status_code not in {200, 201, 409}:
        raise RuntimeError(f"Signup failed: {signup.status_code} {signup.text}")

    login = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    auth_data = _json_or_fail(login)
    token = auth_data.get("access_token")
    if not token:
        raise RuntimeError("Login did not return an access token")

    headers = {"Authorization": f"Bearer {token}"}

    profile_payload = {
        "full_name": "Jane Profile",
        "email": email,
        "phone": "+92 300 1234567",
        "location": "Lahore, Pakistan",
        "linkedin_url": "https://linkedin.com/in/jane-profile",
        "portfolio_url": "https://jane-profile.dev",
        "summary": "Full-stack engineer who ships data-rich product features.",
        "skills": ["Python", "FastAPI", "React", "PostgreSQL", "Docker"],
        "achievements": ["Improved release stability", "Reduced API latency by 28%"],
        "preferred_job_titles": ["Backend Engineer", "Full-Stack Engineer"],
        "desired_salary_min": 180000,
        "desired_salary_max": 320000,
        "willing_to_relocate": False,
        "preferred_work_location": "hybrid",
        "education": [
            {
                "degree": "BS Computer Science",
                "institution": "Example University",
                "field_of_study": "Computer Science",
                "start_year": 2018,
                "end_year": 2022,
                "gpa": "3.8",
                "description": "Graduated with honors.",
            }
        ],
        "work_experience": [
            {
                "job_title": "Software Engineer",
                "company": "Example Corp",
                "location": "Lahore",
                "start_date": "2022-01",
                "end_date": "Present",
                "responsibilities": ["Built internal tools", "Maintained APIs"],
                "achievements": ["Shipped analytics dashboard"],
            }
        ],
        "certifications": [
            {
                "name": "AWS Certified Developer",
                "issuing_org": "AWS",
                "date_earned": "2024-06",
                "credential_url": "https://example.com/cert",
            }
        ],
        "projects": [
            {
                "name": "Analytics Dashboard",
                "description": "Built a dashboard for product metrics and user journeys.",
                "technologies": ["React", "FastAPI", "PostgreSQL"],
                "project_url": "https://example.com/project",
            }
        ],
        "languages": [
            {"name": "English", "proficiency": "Fluent"},
            {"name": "Urdu", "proficiency": "Native"},
        ],
    }

    profile_response = client.post(
        "/profile",
        json=profile_payload,
        headers=headers,
    )
    profile_data = _json_or_fail(profile_response)
    profile = profile_data.get("profile") or {}
    profile_id = profile.get("id")
    if not profile_id:
        raise RuntimeError(f"Profile creation did not return an id: {profile_data!r}")

    job_response = client.post(
        "/jobs/upsert",
        json={
            "title": "Backend Engineer",
            "company": "Smoke Test Labs",
            "description": "Build FastAPI services, PostgreSQL pipelines, and production-ready dashboards.",
            "url": "https://example.com/jobs/backend-engineer",
            "source": "smoke-test",
            "external_id": f"smoke-{timestamp}",
            "location": "Lahore",
            "city": "Lahore",
            "salary": "220000",
            "job_type": "Full-time",
            "experience_required": "2+ years",
        },
    )
    job = _json_or_fail(job_response)
    job_id = job.get("id")
    if not job_id:
        raise RuntimeError(f"Job upsert did not return an id: {job!r}")

    build_response = client.post(
        f"/build_resume/{job_id}",
        headers=headers,
    )
    build_data = _json_or_fail(build_response)
    fixed_resume = str(build_data.get("fixed_resume_text") or "")
    html_resume = str(build_data.get("html_resume") or "")

    required_snippets = [
        "Jane Profile",
        "FastAPI",
        "Analytics Dashboard",
        "AWS Certified Developer",
        "Example University",
    ]
    missing = [snippet for snippet in required_snippets if snippet not in fixed_resume and snippet not in html_resume]
    forbidden = [
        snippet
        for snippet in [
            "Add your degree here",
            "Add your degree and institution here.",
            "Add a relevant project here",
            "Professional summary unavailable",
            "No work experience provided",
            "No education provided",
            "No projects provided",
        ]
        if snippet in fixed_resume or snippet in html_resume
    ]

    if missing:
        raise RuntimeError(f"Resume output is missing real profile data: {missing}")
    if forbidden:
        raise RuntimeError(f"Resume output still contains placeholder text: {forbidden}")

    print("Profile completeness smoke test passed")
    print(f"Created profile {profile_id} and job {job_id} through TestClient")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
