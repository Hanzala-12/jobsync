"""Pytest shared fixtures and configuration."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.database import Base, get_db

# Use a shared in-memory SQLite database accessible across connections/threads.
# This uses the URI form with cache=shared to avoid "no such table" and locking races
# when TestClient runs the app in a separate thread.
DB_URL = "sqlite:///file:tests_db?mode=memory&cache=shared"
engine = create_engine(
    DB_URL,
    connect_args={"check_same_thread": False, "uri": True},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Ensure all model classes are imported so they register with Base.metadata
    import backend.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def seed_db(setup_db):
    # The session-scoped setup already creates the shared in-memory schema.
    # Recreating it here can race with the app thread and lock SQLite.
    import backend.models  # noqa: F401
    yield


@pytest.fixture
def test_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def test_client():
    from backend import main as _main
    from backend.security import create_access_token_for_user
    import backend.database as _database

    app = _main.app

    # Override the app's own get_db reference to ensure the override matches
    app.dependency_overrides[_database.get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    """Return a factory for auth headers."""
    from backend.security import create_access_token_for_user

    def _make(user):
        token = create_access_token_for_user(user)
        return {"Authorization": f"Bearer {token}"}

    return _make
