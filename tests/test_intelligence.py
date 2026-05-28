from __future__ import annotations

import json

from backend.models import User, UserProfile
import backend.routers.intelligence as intelligence_router


def _create_user(test_db, email: str = "intel@example.com"):
    user = User(email=email, hashed_password="hashed", name="Intel User", is_active=True, token_version=0)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


class _FakeLLM:
    def __init__(self, response: str):
        self.response = response

    def ask(self, *args, **kwargs):
        return self.response


def test_skill_gap_analysis_parses_llm_json(test_client, test_db, auth_headers, monkeypatch):
    user = _create_user(test_db, "skillgap@example.com")
    headers = auth_headers(user)
    test_db.add(UserProfile(user_id=user.id, resume_text="Python SQL FastAPI", full_name="Intel", email="intel@example.com", skills=["Python", "SQL"], achievements=[], preferred_job_titles=[], desired_salary_min=0, desired_salary_max=0, willing_to_relocate=False, preferred_work_location="remote", summary=""))
    test_db.commit()

    monkeypatch.setattr(intelligence_router, "LLMProvider", lambda: _FakeLLM(json.dumps({"missing_skills": ["Docker", "Kubernetes"], "frequency": {"Docker": 2, "Kubernetes": 1}})))

    response = test_client.post(
        "/intelligence/skill-gap",
        json={"job_descriptions": ["Need Docker and Kubernetes", "Need Python"]},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["missing_skills"] == ["Docker", "Kubernetes"]
    assert data["frequency"]["Docker"] == 2


def test_interview_prep_falls_back_on_invalid_json(test_client, test_db, auth_headers, monkeypatch):
    user = _create_user(test_db, "interview@example.com")
    headers = auth_headers(user)
    test_db.add(UserProfile(user_id=user.id, resume_text="Python SQL FastAPI", full_name="Intel", email="intel@example.com", skills=["Python", "SQL"], achievements=[], preferred_job_titles=[], desired_salary_min=0, desired_salary_max=0, willing_to_relocate=False, preferred_work_location="remote", summary=""))
    test_db.commit()

    monkeypatch.setattr(intelligence_router, "LLMProvider", lambda: _FakeLLM("not-json"))

    response = test_client.post(
        "/intelligence/interview-prep",
        json={"role": "Backend Engineer", "job_description": "Build APIs"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["questions"] == []
