from __future__ import annotations

import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

ESSENTIAL_TABLES = ["jobs", "universities", "programs", "student_profiles", "applications"]


def check_database() -> bool:
    database_url = (os.getenv("DATABASE_URL") or "").strip()
    if not database_url:
        print("[database] DATABASE_URL is not set")
        return False

    try:
        engine = create_engine(database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            inspector = inspect(connection)
            missing = [table_name for table_name in ESSENTIAL_TABLES if not inspector.has_table(table_name)]
            if missing:
                print(f"[database] Missing tables: {', '.join(missing)}")
                return False
        print("[database] OK")
        return True
    except Exception as exc:
        print(f"[database] Failed: {exc}")
        return False


def check_chroma() -> bool:
    chroma_dir = os.getenv("CHROMA_PERSIST_DIR") or os.getenv("CHROMA_DB_DIR") or str(ROOT / "chroma_db")
    collection_name = os.getenv("CHROMA_COLLECTION_NAME", "jobfit_docs")

    try:
        import chromadb

        client = chromadb.PersistentClient(path=chroma_dir)
        collections = client.list_collections()
        names = [getattr(collection, "name", str(collection)) for collection in collections]
        print(f"[chroma] OK - collections: {', '.join(names) if names else '(none)'}")

        if collection_name in names:
            collection = client.get_collection(collection_name)
            print(f"[chroma] {collection_name} count={collection.count()}")
        else:
            print(f"[chroma] {collection_name} not found yet")

        return True
    except Exception as exc:
        print(f"[chroma] Failed: {exc}")
        return False


def check_api() -> bool:
    base_url = (os.getenv("API_BASE_URL") or "http://127.0.0.1:8000").rstrip("/")
    try:
        response = requests.get(f"{base_url}/health", timeout=20)
        print(f"[api] GET /health -> {response.status_code}")
        if not response.ok:
            print(response.text[:500])
            return False
        return True
    except Exception as exc:
        print(f"[api] Failed: {exc}")
        return False


def main() -> int:
    ok_database = check_database()
    ok_chroma = check_chroma()
    ok_api = check_api()

    if ok_database and ok_chroma and ok_api:
        print("All health checks passed")
        return 0

    print("One or more health checks failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())