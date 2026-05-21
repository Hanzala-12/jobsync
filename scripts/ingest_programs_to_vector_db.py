from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.services.university_match_service import index_programs_to_vector_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Index university programs into ChromaDB")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of programs to index")
    parser.add_argument("--country", type=str, default=None, help="Only index programs for a specific country")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        count = index_programs_to_vector_db(db, limit=args.limit, country=args.country)
        print(f"Indexed {count} programs into the vector database.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
