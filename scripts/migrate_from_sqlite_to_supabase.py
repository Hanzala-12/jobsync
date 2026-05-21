from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable, List

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, inspect, select
from sqlalchemy.dialects.postgresql import insert as pg_insert


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

TARGET_URL = (os.getenv("DATABASE_URL") or "").strip()
SOURCE_SQLITE_URL = (os.getenv("SOURCE_SQLITE_URL") or f"sqlite:///{(ROOT / 'jobsync.db').as_posix()}").strip()


def _chunked(rows: List[dict], size: int = 500) -> Iterable[List[dict]]:
    for index in range(0, len(rows), size):
        yield rows[index : index + size]


def _table_order(inspector) -> list[str]:
    preferred = [
        "jobs",
        "applications",
        "resume_versions",
        "user_profiles",
        "user_preferences",
        "prefetched_jobs",
        "universities",
        "programs",
        "student_profiles",
        "scholarships",
        "saved_programs",
        "applications_study",
        "student_program_matches",
        "university_match_cache",
    ]
    available = set(inspector.get_table_names())
    ordered = [table_name for table_name in preferred if table_name in available]
    extras = sorted(name for name in available if name not in ordered and name != "alembic_version")
    return ordered + extras


def main() -> int:
    if not TARGET_URL:
        print("DATABASE_URL is not set for the Supabase target database.")
        return 1

    source_engine = create_engine(SOURCE_SQLITE_URL, future=True)
    target_engine = create_engine(TARGET_URL, pool_pre_ping=True, future=True)

    source_inspector = inspect(source_engine)
    target_inspector = inspect(target_engine)

    source_tables = _table_order(source_inspector)
    if not source_tables:
        print("No source tables found in SQLite.")
        return 1

    target_metadata = MetaData()
    target_tables = set(target_inspector.get_table_names(schema="public"))
    migrated_tables = 0
    migrated_rows = 0

    with source_engine.connect() as source_connection, target_engine.begin() as target_connection:
        for table_name in source_tables:
            if table_name == "alembic_version":
                continue
            if table_name not in target_tables:
                # Skip source-only tables that are not part of the Supabase schema.
                continue

            source_table = Table(table_name, MetaData(), autoload_with=source_connection)
            target_table = Table(table_name, target_metadata, autoload_with=target_connection)
            rows = [dict(row._mapping) for row in source_connection.execute(select(source_table))]
            if not rows:
                print(f"{table_name}: 0 rows")
                continue

            for batch in _chunked(rows):
                statement = pg_insert(target_table).values(batch).on_conflict_do_nothing()
                target_connection.execute(statement)

            migrated_tables += 1
            migrated_rows += len(rows)
            print(f"{table_name}: migrated {len(rows)} rows")

    print(f"Migration complete. Tables processed: {migrated_tables}, rows read: {migrated_rows}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())