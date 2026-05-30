from __future__ import annotations

from backend.models import User, UserProfile
from backend.security import create_access_token_for_user


def _create_user(test_db, email: str = "cover@example.com"):
    user = User(email=email, hashed_password="hashed", name="Cover User", is_active=True, token_version=0)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


def _create_profile(test_db, user: User):
    profile = UserProfile(
        user_id=user.id,
        resume_text="Resume text: Python SQL FastAPI",
        full_name="Cover User",
        email="cover@example.com",
        skills=["Python", "FastAPI", "SQL"],
        achievements=["Improved API response times"],
        preferred_job_titles=["Backend Engineer"],
        desired_salary_min=0,
        desired_salary_max=0,
        willing_to_relocate=False,
        preferred_work_location="remote",
        summary="Backend engineer",
    )
    test_db.add(profile)
    test_db.commit()
    test_db.refresh(profile)
    return profile


def test_cover_letter_blueprint_generation_and_pdf_download(test_client, test_db, monkeypatch):
    user = _create_user(test_db, "cover-letter@example.com")
    _create_profile(test_db, user)

    from core import cover_letter_blueprint_engine as engine

    async def _fast_enhance(filled_text, job_description):
        return filled_text

    monkeypatch.setattr(engine, "enhance_with_llm", _fast_enhance)

    headers = {"Authorization": f"Bearer {create_access_token_for_user(user)}"}
    payload = {"company": "Acme", "role": "Backend Engineer", "job_description": "Build APIs", "tone": "professional"}

    response = test_client.post(
        "/cover-letter/generate",
        json=payload,
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert "Backend Engineer" in data["draft"]
    assert "Acme" in data["draft"]
    assert "Python" in data["draft"]

    pdf_response = test_client.post("/cover-letter/download", json=payload, headers=headers)
    assert pdf_response.status_code == 200
    assert pdf_response.headers["content-type"] == "application/pdf"
    assert len(pdf_response.content) > 1000
