"""
Core database helpers.

This module re-exports database primitives from `backend.database` so the
SQLAlchemy `Base` is centralized in one place (backend/database.py) and
we avoid circular imports between core and backend modules.
"""
from backend.database import engine, Base, get_db as backend_get_db, init_db as backend_init_db


def init_db():
    """Initialize database tables using the centralized backend init path."""
    backend_init_db()


def get_db():
    """Yield DB session using backend database dependency."""
    # delegate to backend.database.get_db()
    yield from backend_get_db()
