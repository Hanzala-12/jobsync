from __future__ import annotations

import time
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
from backend.models import User, UserProfile
from backend.security import create_access_token_for_user


def _build_test_app():
    import backend.database as database
    from backend import main as main_module

    engine = create_engine(
        "sqlite:///file:cover_letter_blueprint?mode=memory&cache=shared",
        connect_args={"check_same_thread": False, "uri": True},
    )
    session_local = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    main_module.app.dependency_overrides[database.get_db] = override_get_db
    return main_module.app, session_local


def _seed_user(session_local):
    db = session_local()
    try:
        unique_suffix = str(int(time.time() * 1000))
        email = f"blueprint-{unique_suffix}@example.com"
        user = User(email=email, hashed_password="hashed", name="Blueprint User", is_active=True, token_version=0)
        db.add(user)
        db.commit()
        db.refresh(user)

        profile = UserProfile(
            user_id=user.id,
            full_name="Blueprint User",
            email=email,
            skills=["Python", "FastAPI", "SQL"],
            achievements=["Reduced API latency by 35%"],
            preferred_job_titles=["Backend Engineer"],
            summary="Backend engineer focused on APIs",
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
        token = create_access_token_for_user(user)
        return user, token
    finally:
        db.close()


def _measure(client, headers, payload):
    started = time.perf_counter()
    response = client.post("/cover-letter/generate", json=payload, headers=headers)
    elapsed = time.perf_counter() - started
    response.raise_for_status()
    return elapsed, response.json()


def main() -> int:
    app, session_local = _build_test_app()
    user, token = _seed_user(session_local)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "company": "Acme Labs",
        "role": "Backend Engineer",
        "job_description": "We need someone to build APIs, optimize SQL queries, and ship reliable features fast.",
        "tone": "professional",
    }

    import core.cover_letter_blueprint_engine as engine

    async def fast_blueprint(filled_text, job_description):
        return filled_text

    async def polished_blueprint(filled_text, job_description):
        body = next((section for section in filled_text.get("sections", []) if section.get("name") == "body"), None)
        if body:
            body["text"] = body["text"] + " We value speed, ownership, and clean execution."
            filled_text["text"] = "\n\n".join(section["text"] for section in filled_text["sections"])
        return filled_text

    original_enhance = engine.enhance_with_llm
    try:
        engine.enhance_with_llm = fast_blueprint
        blueprint_only_elapsed, blueprint_only_data = _measure(TestClient(app), headers, payload)

        engine.enhance_with_llm = polished_blueprint
        polished_elapsed, polished_data = _measure(TestClient(app), headers, payload)

        pdf_response = TestClient(app).post("/cover-letter/download", json=payload, headers=headers)
        pdf_response.raise_for_status()
        pdf_bytes = pdf_response.content
    finally:
        engine.enhance_with_llm = original_enhance

    assert blueprint_only_elapsed < 1.0, f"Blueprint generation was too slow: {blueprint_only_elapsed:.3f}s"
    assert polished_elapsed < 2.0, f"Polished generation was too slow: {polished_elapsed:.3f}s"
    assert "Backend Engineer" in blueprint_only_data["draft"]
    assert "Acme Labs" in blueprint_only_data["draft"]
    assert "Python" in blueprint_only_data["draft"]
    assert "Acme Labs" in polished_data["draft"]
    assert len(pdf_bytes) > 1000, "Downloaded PDF was empty"

    print(f"blueprint_only_seconds={blueprint_only_elapsed:.3f}")
    print(f"polished_seconds={polished_elapsed:.3f}")
    print(f"pdf_bytes={len(pdf_bytes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())