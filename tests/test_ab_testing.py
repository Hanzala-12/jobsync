from __future__ import annotations

from importlib import reload

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


def test_ab_assignment_and_event_logging(monkeypatch):
    monkeypatch.setenv("ENABLE_AB_TESTING", "true")

    from backend.database import Base
    from backend.models import ABTest, ABTestEvent, User
    import backend.services.ab_testing_service as ab_service

    reload(ab_service)

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    test_db = SessionLocal()

    user = User(email="ab@example.com", hashed_password="x", is_active=True)
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    ab_service.ensure_default_tests(test_db)
    tests = test_db.query(ABTest).all()
    assert len(tests) >= 3

    contexts = ab_service.assign_user_for_all_features(test_db, user.id)
    assert "matching_algorithm" in contexts

    event_id = ab_service.log_event(
        test_db,
        user_id=user.id,
        feature_key=ab_service.FEATURE_MATCHING,
        event_type="match_request",
        match_score=82,
        user_clicks={"saved": False, "applied": False},
    )
    assert event_id is not None

    saved = test_db.query(ABTestEvent).filter(ABTestEvent.id == event_id).first()
    assert saved is not None
    assert saved.event_type == "match_request"
    assert float(saved.match_score) == 82.0

    test_db.close()
