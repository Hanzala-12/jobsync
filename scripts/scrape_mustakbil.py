from __future__ import annotations

import argparse
import logging
from backend.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape_mustakbil")


def main(limit: int | None = None):
    db = SessionLocal()
    try:
        from scrapers.mustakbil_scraper import run
        if limit:
            results = run(db, max_results=limit)
        else:
            results = run(db)
        logger.info("Mustakbil: inserted/updated %d items", len(results))
    except Exception as exc:
        logger.exception("Mustakbil scraper failed: %s", exc)
    finally:
        db.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    main(limit=args.limit)
