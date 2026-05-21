from __future__ import annotations

import argparse
import time
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.services.university_match_service import refresh_match_cache


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh cached university-program matches")
    parser.add_argument("--profile-limit", type=int, default=None, help="Limit the number of student profiles to refresh")
    parser.add_argument("--program-limit", type=int, default=50, help="Number of programs to refresh per profile")
    parser.add_argument("--daemon", action="store_true", help="Run continuously and refresh on a fixed interval")
    parser.add_argument("--interval-hours", type=int, default=24, help="Daemon refresh interval in hours")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.daemon:
            while True:
                results = refresh_match_cache(db, profile_limit=args.profile_limit, program_limit=args.program_limit)
                print("Match cache refresh complete:")
                print(f"- profiles: {results['profiles']}")
                print(f"- matches: {results['matches']}")
                time.sleep(max(60, args.interval_hours * 3600))
        else:
            results = refresh_match_cache(db, profile_limit=args.profile_limit, program_limit=args.program_limit)
            print("Match cache refresh complete:")
            print(f"- profiles: {results['profiles']}")
            print(f"- matches: {results['matches']}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
