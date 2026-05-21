from __future__ import annotations

import logging
from backend.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape_erasmus")


def main(limit: int | None = None):
    db = SessionLocal()
    try:
        from scrapers.erasmus_scraper import run, run_sample
        results = run_sample(db) if limit else run(db)
        logger.info("Erasmus: inserted/updated %d items", len(results))
    except Exception as exc:
        logger.exception("Erasmus scraper failed: %s", exc)
    finally:
        db.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    main(limit=args.limit)
