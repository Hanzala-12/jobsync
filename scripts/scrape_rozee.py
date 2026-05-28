from __future__ import annotations

import argparse
import logging
import sys
from backend.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape_rozee")


def main(limit: int | None = None):
    db = SessionLocal()
    try:
        from scrapers.rozee_scraper import run
        if limit:
            logger.info("Running rozee run with limit=%s", limit)
            results = run(db, max_results=limit)
        else:
            logger.info("Running full rozee run")
            results = run(db)
        logger.info("Rozee: inserted/updated %d items", len(results))
    except Exception as exc:
        logger.exception("Rozee scraper failed: %s", exc)
    finally:
        db.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    main(limit=args.limit)
