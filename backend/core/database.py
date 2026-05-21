"""
Core database helpers (vendored for backend deployment).
"""
from backend.database import engine, Base, get_db as backend_get_db


def init_db():
    try:
        from alembic.config import Config
        from alembic import command
        import os

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        alembic_ini_path = os.path.join(base_dir, "backend", "alembic.ini")

        alembic_cfg = Config(alembic_ini_path)
        command.upgrade(alembic_cfg, "head")
        print("Alembic migrations completed successfully.")
    except Exception as e:
        print(f"Alembic migration failed: {e}")


def get_db():
    yield from backend_get_db()
