from __future__ import annotations

import sys
import types

from backend.models import User, UserProfile


def _create_user(test_db, email: str = "cover@example.com"):
    user = User(email=email, hashed_password="hashed", name="Cover User", is_active=True, token_version=0)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user


class _AsyncResult:
    def __init__(self, result):
        self._result = result

    def __await__(self):
        async def _inner():
            return self._result

        return _inner().__await__()


async def _fake_generate(*args, **kwargs):
    return "Draft cover letter", ["source-1"], []


def test_cover_letter_generation_uses_rag_helpers(test_client, test_db, auth_headers, monkeypatch):
    user = _create_user(test_db, "cover-letter@example.com")
    headers = auth_headers(user)
    test_db.add(UserProfile(user_id=user.id, resume_text="Resume text: Python SQL FastAPI", full_name="Cover User", email="cover@example.com", skills=["Python"], achievements=[], preferred_job_titles=[], desired_salary_min=0, desired_salary_max=0, willing_to_relocate=False, preferred_work_location="remote", summary="Backend engineer"))
    test_db.commit()

    fake_module = types.ModuleType("core.rag_service")
    fake_module.generate_cover_letter_with_rag_async = _fake_generate
    fake_module.save_cover_letter_artifacts = lambda *args, **kwargs: {"text_path": "cover.txt", "json_path": "cover.json"}
    monkeypatch.setitem(sys.modules, "core.rag_service", fake_module)

    response = test_client.post(
        "/cover-letter/generate",
        json={"company": "Acme", "role": "Backend Engineer", "job_description": "Build APIs", "tone": "professional"},
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["draft"] == "Draft cover letter"
    assert data["source_ids"] == ["source-1"]
