import os
from sqlalchemy import create_engine, text
import sys

url = os.getenv('DATABASE_URL')
if not url:
    print('DATABASE_URL not set; skipping summary')
    sys.exit(0)

engine = create_engine(url)
with engine.connect() as conn:
    total = conn.execute(text('SELECT COUNT(1) FROM program_scrape_jobs')).scalar() or 0
    failed = conn.execute(text("SELECT COUNT(1) FROM program_scrape_jobs WHERE status='failed'")).scalar() or 0
    completed = conn.execute(text("SELECT COUNT(1) FROM program_scrape_jobs WHERE status='completed'")).scalar() or 0
    blocked = conn.execute(text("SELECT COUNT(1) FROM program_scrape_jobs WHERE status='blocked'")).scalar() or 0
    print(f'Total jobs: {total} completed: {completed} failed: {failed} blocked: {blocked}')
    rate = (failed / total) if total else 0
    if rate > 0.20:
        print('Failure rate too high:', rate)
        sys.exit(1)
    else:
        print('Failure rate acceptable:', rate)
        sys.exit(0)
