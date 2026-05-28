from __future__ import annotations

import sys
import time
from pathlib import Path

from starlette.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.main import app

CLIENT = TestClient(app)

FORBIDDEN_PHRASES = [
    "Add your degree and institution here.",
    "Add your degree here",
    "Add your most recent role here",
    "Add one relevant project that demonstrates direct job alignment.",
    "Professional summary unavailable",
    "No work experience provided",
    "No education provided",
    "No projects provided",
]


def _json_or_fail(response) -> dict:
    try:
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(f"HTTP {response.status_code}: {response.text}") from exc
    data = response.json()
    if not isinstance(data, dict):
        raise RuntimeError(f"Unexpected response payload: {data!r}")
    return data


def main() -> int:
    timestamp = int(time.time() * 1000)
    email = f"resume-tailor-{timestamp}@example.com"
    password = "Testpass123!"

    signup = CLIENT.post(
        "/auth/signup",
        json={"email": email, "password": password, "name": "Resume Tailor"},
    )
    if signup.status_code not in {200, 201, 409}:
        raise RuntimeError(f"Signup failed: {signup.status_code} {signup.text}")

    login = CLIENT.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    auth_data = _json_or_fail(login)
    token = auth_data.get("access_token")
    if not token:
        raise RuntimeError("Login did not return an access token")

    headers = {"Authorization": f"Bearer {token}"}

    profile_payload = {
        "full_name": "Amina Khan",
        "email": email,
        "phone": "+92 300 1234567",
        "location": "Karachi, Pakistan",
        "summary": "Python and FastAPI engineer with a strong focus on production systems.",
        "skills": ["Python", "FastAPI", "SQL", "Docker", "AWS"],
        "education": [
            {
                "degree": "BS Computer Science",
                "institution": "National University",
                "field_of_study": "Computer Science",
                "start_year": 2016,
                "end_year": 2020,
            }
        ],
        "work_experience": [
            {
                "job_title": "Backend Engineer",
                "company": "Example Labs",
                "location": "Karachi",
                "start_date": "2021-01",
                "end_date": "Present",
                "responsibilities": ["Built FastAPI services", "Improved observability"],
                "achievements": ["Reduced API latency by 22%"],
            }
        ],
        "projects": [
            {
                "name": "Analytics Pipeline",
                "description": "Built a Python pipeline for ingestion and analytics reporting.",
                "technologies": ["Python", "PostgreSQL", "Docker"],
            }
        ],
    }
    profile_response = CLIENT.post("/profile", json=profile_payload, headers=headers)
    _json_or_fail(profile_response)

    job_response = CLIENT.post(
        "/jobs/upsert",
        json={
            "title": "Backend Engineer",
            "company": "Tailored Hiring Co",
            "description": "Build FastAPI services, ship production-ready APIs, and improve reliability with Python and AWS.",
            "url": f"https://example.com/jobs/backend-engineer-{timestamp}",
            "source": "resume-tailoring-test",
            "external_id": f"resume-tailoring-{timestamp}",
            "location": "Karachi",
            "city": "Karachi",
            "salary": "250000",
            "job_type": "Full-time",
            "experience_required": "2+ years",
        },
    )
    job = _json_or_fail(job_response)
    job_id = job.get("id")
    if not job_id:
        raise RuntimeError(f"Job upsert did not return an id: {job!r}")

    build_response = CLIENT.post(f"/build_resume/{job_id}", headers=headers)
    build_data = _json_or_fail(build_response)
    fixed_resume = str(build_data.get("fixed_resume_text") or "")
    html_resume = str(build_data.get("html_resume") or "")

    found = [phrase for phrase in FORBIDDEN_PHRASES if phrase in fixed_resume or phrase in html_resume]
    if found:
        raise RuntimeError(f"Resume output still contains placeholder text: {found}")

    if "FastAPI" not in fixed_resume and "FastAPI" not in html_resume:
        raise RuntimeError("Resume output is missing job-relevant profile content")

    print("Resume tailoring test passed")
    print(f"Created user {email} and job {job_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
