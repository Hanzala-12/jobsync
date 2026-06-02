import logging
import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip()
if not DATABASE_URL:
    fallback_path = os.getenv("SQLITE_FALLBACK_PATH", "/tmp/jobsync.db")
    DATABASE_URL = f"sqlite:///{fallback_path}"
    logging.warning(
        "DATABASE_URL is not set. Falling back to local SQLite database at %s. "
        "This is suitable for development only; configure DATABASE_URL for production.",
        fallback_path,
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
