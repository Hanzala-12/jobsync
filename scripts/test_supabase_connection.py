from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

ESSENTIAL_TABLES = [
    "jobs",
    "universities",
    "programs",
    "student_profiles",
    "applications",
]


def main() -> int:
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        print("DATABASE_URL is not set.")
        return 1

    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            version = connection.execute(text("SELECT version();")).scalar_one()
            print("✅ Connected to Supabase successfully")
            print(f"PostgreSQL version: {version}")

            inspector = inspect(connection)
            tables = inspector.get_table_names(schema="public")
            print("Public schema tables:")
            for table_name in tables:
                print(f"- {table_name}")

            missing = [table_name for table_name in ESSENTIAL_TABLES if table_name not in tables]
            if missing:
                print(f"Missing essential tables: {', '.join(missing)}")
                return 1

        return 0
    except Exception as exc:
        print(f"Connection test failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())