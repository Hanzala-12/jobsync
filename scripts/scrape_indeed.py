from __future__ import annotations

import argparse
import logging
from backend.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape_indeed")


def main(limit: int | None = None):
    db = SessionLocal()
    try:
        from scrapers.indeed_scraper import run, run_sample
        if limit:
            results = run_sample(db)
        else:
            results = run(db)
        logger.info("Indeed: inserted/updated %d items", len(results))
    except Exception as exc:
        logger.exception("Indeed scraper failed: %s", exc)
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    main(limit=args.limit)
