#!/usr/bin/env python3
"""
Seed a full profile for the test user used by scripts/test_resume_output.py
"""
import os
import requests

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
EMAIL = os.environ.get("TEST_EMAIL", "autotest+e2e2026@example.com")
PASSWORD = os.environ.get("TEST_PASSWORD", "TestPass123!")


def login(email, password):
    url = f"{API_BASE}/auth/login"
    resp = requests.post(url, json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json().get("access_token")


def create_profile(token):
    url = f"{API_BASE}/profile"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    payload = {
        "full_name": "E2E Tester",
        "email": EMAIL,
        "phone": "+923165450583",
        "location": "Karachi, Pakistan",
        "summary": "Software engineer with experience building web apps, APIs, and automated testing.",
        "skills": "Python, SQL, AWS, Docker, Kubernetes, CI/CD, FastAPI, TypeScript",
        "work_experience": [
            {
                "job_title": "Senior Backend Engineer",
                "company": "Acme Co",
                "start_date": "2019-01",
                "end_date": "2022-06",
                "responsibilities": ["Built REST APIs","Maintained CI/CD pipelines"],
                "achievements": ["Reduced deployment time by 60%","Improved test coverage by 40%"]
            }
        ],
        "education": [
            {"degree": "B.S. Computer Science", "institution": "Karachi University", "start_year": "2014", "end_year": "2018", "gpa": "3.4"}
        ],
        "projects": [
            {"name": "Job Match Engine", "description": "Built job matching and scoring engine", "technologies": ["Python","FastAPI","Postgres"]}
        ],
        "certifications": [
            {"name": "Certified Kubernetes Administrator", "issuing_org": "CNCF", "date_earned": "2022"}
        ],
        "languages": [
            {"name": "English", "proficiency": "Fluent"},
            {"name": "Urdu", "proficiency": "Native"}
        ]
    }
    resp = requests.post(url, json=payload, headers=headers)
    resp.raise_for_status()
    profile = resp.json().get("profile") or {}
    profile_id = profile.get("id")
    if profile_id:
        sel = requests.post(f"{API_BASE}/profile/select/{profile_id}", headers={"Authorization": f"Bearer {token}"}, timeout=20)
        sel.raise_for_status()
        print(f"Profile seeded and selected: {profile_id}")
    else:
        print("Profile seeded:", resp.json())


if __name__ == '__main__':
    tok = login(EMAIL, PASSWORD)
    create_profile(tok)
