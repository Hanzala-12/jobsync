from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import MetaData, Table, create_engine, delete, select


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")


def main() -> int:
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        print("DATABASE_URL is not set.")
        return 1

    external_id = f"jobsync_test_crud_{uuid.uuid4().hex}"
    engine = create_engine(database_url, pool_pre_ping=True)
    metadata = MetaData()

    try:
        with engine.begin() as connection:
            jobs_table = Table("jobs", metadata, autoload_with=connection)

            connection.execute(delete(jobs_table).where(jobs_table.c.external_id == external_id))

            insert_payload = {
                "source": "test_suite",
                "external_id": external_id,
                "title": "CRUD Verification Job",
                "company": "JobSync Test",
                "location": "Remote",
                "description": "Temporary record used to verify insert/read/delete against Supabase.",
                "url": "https://example.com/test-crud",
                "city": "Remote",
                "is_active": True,
                "possibly_inactive": False,
            }
            connection.execute(jobs_table.insert().values(**insert_payload))

            row = connection.execute(
                select(jobs_table).where(jobs_table.c.external_id == external_id)
            ).mappings().first()
            if not row:
                print("CRUD test failed: inserted row was not found")
                return 1
            print(f"Inserted row id={row['id']} external_id={row['external_id']}")

            connection.execute(delete(jobs_table).where(jobs_table.c.external_id == external_id))

            deleted = connection.execute(
                select(jobs_table.c.id).where(jobs_table.c.external_id == external_id)
            ).first()
            if deleted:
                print("CRUD test failed: row still exists after delete")
                return 1

        print("CRUD test passed")
        return 0
    except Exception as exc:
        print(f"CRUD test failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())