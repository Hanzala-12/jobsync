import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()

# Support a production DATABASE_URL (Postgres). If missing, fall back to a local SQLite for
# development convenience. This avoids hard failures in local dev while ensuring production
# uses the provided DATABASE_URL (e.g. Supabase).
if DATABASE_URL:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
else:
    # Local development fallback
    sqlite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "dev.db"))
    sqlite_url = f"sqlite:///{sqlite_path}"
    engine = create_engine(sqlite_url, connect_args={"check_same_thread": False}, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
