"""Background job indexer to pre-fetch popular job queries into SQLite prefetched_jobs table.

Run as a separate process: `python -m backend.job_indexer` or `python backend/job_indexer.py` from project root.
"""

import os
import time
import logging
from datetime import datetime
from backend.services import job_apis
from backend.database import engine
from core.database import init_db
import json

_logger = logging.getLogger(__name__)

PREFETCH_INTERVAL_HOURS = float(os.getenv("PREFETCH_INTERVAL_HOURS", "1"))
QUERIES = os.getenv("PREFETCH_QUERIES", "software engineer,data analyst,data scientist,product manager,designer,devops").split(",")

SLEEP_SECONDS = int(PREFETCH_INTERVAL_HOURS * 3600)


def _upsert_prefetched(job: dict):
    job_id = job.get("external_id") or job.get("url") or f"{job.get('title')}-{job.get('company')}"
    title = job.get("title") or ""
    company = job.get("company") or ""
    description = job.get("description") or ""
    source = job.get("source") or ""
    fetched_at = datetime.utcnow()

    with engine.begin() as conn:
        try:
            conn.execute(
                "INSERT OR REPLACE INTO prefetched_jobs (job_id, title, company, description, source, fetched_at) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, title, company, description, source, fetched_at.strftime("%Y-%m-%d %H:%M:%S")),
            )
        except Exception as exc:
            _logger.warning("Failed to upsert prefetched job: %s", exc)


def fetch_and_store():
    for q in QUERIES:
        q = q.strip()
        if not q:
            continue
        try:
            _logger.info("Indexer fetching for query: %s", q)
            jobs = job_apis.search_jobs(q, location="Pakistan", country_code="pk")
        except Exception as exc:
            _logger.warning("Indexer failed to fetch for query %s: %s", q, exc)
            continue

        _logger.info("Indexer found %d jobs for query %s", len(jobs), q)
        for job in jobs:
            _upsert_prefetched(job)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    _logger.info("Initializing database...")
    init_db()
    _logger.info("Starting job indexer with interval %sh", PREFETCH_INTERVAL_HOURS)

    while True:
        try:
            _logger.info("Running fetch and store cycle...")
            fetch_and_store()
            _logger.info("Fetch and store cycle complete.")
        except Exception as exc:
            _logger.exception("Job indexer loop failed: %s", exc)
        _logger.info("Job indexer sleeping for %s seconds", SLEEP_SECONDS)
        time.sleep(SLEEP_SECONDS)


if __name__ == "__main__":
    main()
