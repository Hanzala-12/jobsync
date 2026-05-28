from __future__ import annotations

import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import Base, SessionLocal, engine
from scripts.ingest_universities import _mock_program_payload, _upsert_program, _upsert_university

EUROPE_COUNTRIES = [
    "Germany",
    "France",
    "Spain",
    "Italy",
    "Netherlands",
    "United Kingdom",
    "Switzerland",
    "Sweden",
    "Poland",
    "Ireland",
]


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    processed = 0
    try:
        for country in EUROPE_COUNTRIES:
            response = requests.get("http://universities.hipolabs.com/search", params={"country": country}, timeout=30)
            response.raise_for_status()
            payload = response.json()
            count = 0
            for item in payload[:40]:
                university = _upsert_university(db, item, processed)
                db.flush()
                for program_payload in _mock_program_payload(processed, university):
                    program = _upsert_program(db, university, program_payload)
                    db.flush()
                processed += 1
                count += 1
            db.commit()
            print(f"{country}: {count}")
        print(f"processed: {processed}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
