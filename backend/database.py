from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError

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


def init_db():
    """Create tables and backfill missing columns for existing SQLite DBs."""
    Base.metadata.create_all(bind=engine)

    # SQLite won't add new columns on create_all() for already-existing tables,
    # so we patch the applications table in place when needed.
    with engine.begin() as connection:
        inspector = inspect(connection)
        if not inspector.has_table("applications"):
            return

        existing_columns = {column["name"] for column in inspector.get_columns("applications")}
        required_columns = {
            "source": "ALTER TABLE applications ADD COLUMN source VARCHAR",
            "interview_date": "ALTER TABLE applications ADD COLUMN interview_date DATETIME",
            "follow_up_date": "ALTER TABLE applications ADD COLUMN follow_up_date DATETIME",
            "next_action": "ALTER TABLE applications ADD COLUMN next_action VARCHAR",
        }

        for column_name, alter_sql in required_columns.items():
            if column_name not in existing_columns:
                connection.execute(text(alter_sql))
