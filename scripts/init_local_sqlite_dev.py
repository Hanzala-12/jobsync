from __future__ import annotations

import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize a local SQLite database for development")
    parser.add_argument("--path", default=os.getenv("LOCAL_SQLITE_DB_PATH", "./jobsync_local.db"), help="SQLite database path")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    db_path = Path(args.path).expanduser().resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"

    from backend.database import Base
    import backend.models  # noqa: F401

    engine = create_engine(f"sqlite:///{db_path.as_posix()}")
    Base.metadata.create_all(bind=engine)
    print({"database_url": f"sqlite:///{db_path.as_posix()}", "status": "initialized"})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())