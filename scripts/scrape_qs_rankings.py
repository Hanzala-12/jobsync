from __future__ import annotations

import logging
from backend.database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("scrape_qs")


def main(limit: int | None = None):
    db = SessionLocal()
    try:
        # Placeholder: implement QS scraping logic or reuse existing scrapers if available
        from scrapers.qs_scraper import run, run_sample
        results = run_sample(db) if limit else run(db)
        logger.info("QS rankings: inserted/updated %d items", len(results))
    except Exception as exc:
        logger.exception("QS scraper failed: %s", exc)
    finally:
        db.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    main(limit=args.limit)
