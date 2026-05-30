import os
import sys
repo_root = os.getcwd()
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from backend.services.job_apis import search_jobs
from backend.routers.jobs import _upsert_jobs
from backend.database import SessionLocal


def run():
    print('Fetching live jobs for "machine learning engineer"...')
    jobs = search_jobs('machine learning engineer', location='Pakistan', country_code='pk')
    print('Fetched', len(jobs), 'jobs')
    if not jobs:
        print('No live jobs found to upsert')
        return
    with SessionLocal() as db:
        saved = _upsert_jobs(db, jobs)
        print('Upserted', len(saved), 'jobs to DB')


if __name__ == '__main__':
    run()
