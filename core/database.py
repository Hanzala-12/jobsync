"""
Core database helpers.

This module re-exports database primitives from `backend.database` so the
SQLAlchemy `Base` is centralized in one place (backend/database.py) and
we avoid circular imports between core and backend modules.
"""
from backend.database import engine, Base, get_db as backend_get_db


def init_db():
    """Initialize database tables using Alembic migrations."""
    try:
        from alembic.config import Config
        from alembic import command
        import os
        
        # Resolve backend/alembic.ini path relative to this file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini_path = os.path.join(base_dir, "backend", "alembic.ini")
        
        alembic_cfg = Config(alembic_ini_path)
        command.upgrade(alembic_cfg, "head")
        print("Alembic migrations completed successfully.")
    except Exception as e:
        print(f"Alembic migration failed: {e}")


def get_db():
    """Yield DB session using backend database dependency."""
    # delegate to backend.database.get_db()
    yield from backend_get_db()
