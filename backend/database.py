import os
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

_repo_root = Path(__file__).resolve().parents[1]
_default_sqlite_path = (_repo_root / "jobsync.db").resolve()
_default_database_url = f"sqlite:///{_default_sqlite_path.as_posix()}"

DATABASE_URL = os.getenv("DATABASE_URL", _default_database_url)
SQLITE_TIMEOUT_SECONDS = max(30, int(os.getenv("SQLITE_TIMEOUT_SECONDS", "30")))

engine_kwargs = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": SQLITE_TIMEOUT_SECONDS,
    }

engine = create_engine(DATABASE_URL, **engine_kwargs)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if not DATABASE_URL.startswith("sqlite"):
        return

    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute(f"PRAGMA busy_timeout={SQLITE_TIMEOUT_SECONDS * 1000};")
    finally:
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
