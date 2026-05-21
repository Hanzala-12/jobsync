from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import DATABASE_URL  # noqa: E402


ESSENTIAL_TABLES = [
    "jobs",
    "universities",
    "programs",
    "student_profiles",
]


def main() -> int:
    database_url = (DATABASE_URL or os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        print("DATABASE_URL is not set.")
        return 1

    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version();")).scalar_one()
            print(f"PostgreSQL version: {version}")

            tables = connection.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;")
            ).scalars().all()
            print("Public schema tables:")
            for table_name in tables:
                print(f"- {table_name}")

            missing = [table_name for table_name in ESSENTIAL_TABLES if table_name not in tables]
            if missing:
                print(f"Missing essential tables: {', '.join(missing)}")
                return 1

        return 0
    except Exception as exc:
        print(f"Supabase connection verification failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())