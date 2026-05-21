from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import inspect


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import engine  # noqa: E402


REQUIRED_TABLES = [
    "jobs",
    "applications",
    "resume_versions",
    "prefetched_jobs",
    "user_profiles",
    "user_preferences",
    "universities",
    "programs",
    "student_profiles",
    "scholarships",
    "saved_programs",
    "applications_study",
    "student_program_matches",
    "university_match_cache",
]


def _check_sqlite_schema() -> list[str]:
    inspector = inspect(engine)
    return [table_name for table_name in REQUIRED_TABLES if not inspector.has_table(table_name)]


def _check_chroma_collection() -> str:
    import chromadb

    collection_name = os.getenv("CHROMA_COLLECTION_NAME", "jobfit_docs")
    persist_dir = os.getenv("CHROMA_PERSIST_DIR") or os.getenv("CHROMA_DB_DIR") or str(ROOT / "chroma_db")
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_collection(collection_name)
    return f"{collection.name} (count={collection.count()})"


def main() -> int:
    missing_tables = _check_sqlite_schema()
    if missing_tables:
        print(f"Missing required tables: {', '.join(missing_tables)}")
        return 1

    try:
        collection_info = _check_chroma_collection()
    except Exception as exc:
        print(f"ChromaDB check failed: {exc}")
        return 1

    print("Schema validation passed")
    print(f"ChromaDB collection ready: {collection_info}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())