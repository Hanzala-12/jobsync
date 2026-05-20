from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./jobsync.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_columns(connection, table_name: str, required_columns: dict):
    inspector = inspect(connection)
    if not inspector.has_table(table_name):
        return

    existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
    for column_name, alter_sql in required_columns.items():
        if column_name not in existing_columns:
            connection.execute(text(alter_sql))


def init_db():
    """Create tables and backfill missing columns for existing SQLite DBs."""
    Base.metadata.create_all(bind=engine)

    with engine.begin() as connection:
        _ensure_columns(
            connection,
            "applications",
            {
                "source": "ALTER TABLE applications ADD COLUMN source VARCHAR",
                "interview_date": "ALTER TABLE applications ADD COLUMN interview_date DATETIME",
                "follow_up_date": "ALTER TABLE applications ADD COLUMN follow_up_date DATETIME",
                "next_action": "ALTER TABLE applications ADD COLUMN next_action VARCHAR",
                "resume_version": "ALTER TABLE applications ADD COLUMN resume_version VARCHAR",
                "contact_email": "ALTER TABLE applications ADD COLUMN contact_email VARCHAR",
                "notes": "ALTER TABLE applications ADD COLUMN notes TEXT",
            },
        )

        _ensure_columns(
            connection,
            "jobs",
            {
                "salary": "ALTER TABLE jobs ADD COLUMN salary VARCHAR",
                "city": "ALTER TABLE jobs ADD COLUMN city VARCHAR",
                "apply_url": "ALTER TABLE jobs ADD COLUMN apply_url VARCHAR",
                "job_type": "ALTER TABLE jobs ADD COLUMN job_type VARCHAR",
                "experience_required": "ALTER TABLE jobs ADD COLUMN experience_required VARCHAR",
                "scraped_at": "ALTER TABLE jobs ADD COLUMN scraped_at DATETIME",
                "dedup_fingerprint": "ALTER TABLE jobs ADD COLUMN dedup_fingerprint VARCHAR",
                "sources_seen": "ALTER TABLE jobs ADD COLUMN sources_seen TEXT",
                "first_seen_at": "ALTER TABLE jobs ADD COLUMN first_seen_at DATETIME",
                "last_seen_at": "ALTER TABLE jobs ADD COLUMN last_seen_at DATETIME",
                "possibly_inactive": "ALTER TABLE jobs ADD COLUMN possibly_inactive BOOLEAN DEFAULT 0",
                "is_active": "ALTER TABLE jobs ADD COLUMN is_active BOOLEAN DEFAULT 1",
            },
        )

        inspector = inspect(connection)
        if inspector.has_table("jobs"):
            index_names = {index["name"] for index in inspector.get_indexes("jobs")}
            if "ix_jobs_dedup_fingerprint" not in index_names:
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_dedup_fingerprint ON jobs (dedup_fingerprint)"))
            if "ix_jobs_city" not in index_names:
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_jobs_city ON jobs (city)"))

        _ensure_columns(
            connection,
            "resume_versions",
            {
                "used_for": "ALTER TABLE resume_versions ADD COLUMN used_for VARCHAR",
                "ats_score": "ALTER TABLE resume_versions ADD COLUMN ats_score INTEGER",
            },
        )
        # Create prefetched_jobs table for background indexer/cache
        connection.execute(
            text(
                """
            CREATE TABLE IF NOT EXISTS prefetched_jobs (
                job_id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                description TEXT,
                source TEXT,
                fetched_at DATETIME
            )
            """
            )
        )
        # Index for faster lookups by fetched_at
        try:
            connection.execute(text("CREATE INDEX IF NOT EXISTS ix_prefetched_jobs_fetched_at ON prefetched_jobs (fetched_at)"))
        except Exception:
            pass
