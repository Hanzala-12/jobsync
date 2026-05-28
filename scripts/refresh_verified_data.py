from __future__ import annotations

import argparse
import os
import time
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.university_verification_service import ENABLE_LIVE_VERIFICATION, run_refresh_verified_data_job
from backend.services.program_scraper import ENABLE_ON_DEMAND_SCRAPING
from backend.tasks.refresh_tasks import dispatch_refresh_verified_data


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh the live university verification cache")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--country", type=str, default=None)
    parser.add_argument("--priority-limit", type=int, default=100, help="Maximum number of searched programs to prioritize")
    parser.add_argument("--priority-age-days", type=int, default=30, help="Only prioritize searches from this many days back")
    parser.add_argument("--sleep-seconds", type=float, default=0.0, help="Optional pause between refresh runs")
    args = parser.parse_args()

    if not ENABLE_LIVE_VERIFICATION:
        print("ENABLE_LIVE_VERIFICATION is disabled; the refresh will use cached/static fallbacks only.")
    if not ENABLE_ON_DEMAND_SCRAPING:
        print("ENABLE_ON_DEMAND_SCRAPING is disabled; popularity-based scraping will be skipped.")

    enable_celery = os.getenv("ENABLE_CELERY", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not ENABLE_ON_DEMAND_SCRAPING:
        print("ENABLE_ON_DEMAND_SCRAPING is disabled; priority refresh will be skipped.")

    if enable_celery:
        result = dispatch_refresh_verified_data(
            limit=args.limit,
            country=args.country,
            priority_limit=max(1, int(args.priority_limit)),
            priority_age_days=max(1, int(args.priority_age_days)),
        )
        print(result)
    else:
        result = run_refresh_verified_data_job(
            limit=args.limit,
            country=args.country,
            priority_limit=max(1, int(args.priority_limit)),
            priority_age_days=max(1, int(args.priority_age_days)),
        )
        print(result)

    if args.sleep_seconds > 0:
        time.sleep(args.sleep_seconds)


if __name__ == "__main__":
    main()
