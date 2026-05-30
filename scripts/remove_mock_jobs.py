from __future__ import annotations

import sys
from pathlib import Path

from sqlalchemy import func, or_

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.models import Job


def _mock_job_filter():
    company_names = [
        "Brand Demand",
        "Test Company",
        "TestCo",
        "SeedAI Labs",
        "VectorAI",
        "DeepSignal",
    ]

    return or_(
        Job.source.is_(None),
        func.lower(Job.source) == "seed",
        func.lower(func.coalesce(Job.external_id, "")).like("seed:%"),
        func.lower(func.coalesce(Job.url, "")).like("%example.com%"),
        func.lower(func.coalesce(Job.apply_url, "")).like("%example.com%"),
        func.lower(func.coalesce(Job.company, "")).in_([name.lower() for name in company_names]),
    )


def main() -> int:
    db = SessionLocal()
    try:
        mock_query = db.query(Job).filter(_mock_job_filter())
        total = mock_query.count()
        if total == 0:
            print("No mock jobs found.")
            return 0

        deleted = mock_query.delete(synchronize_session=False)
        db.commit()
        print(f"Deleted {deleted} mock jobs.")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())