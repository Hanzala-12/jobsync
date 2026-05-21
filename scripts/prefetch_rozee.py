"""Prefetch Rozee jobs and POST them to a target backend's /jobs/upsert endpoint.

Usage:
  - Set environment variable BACKEND_URL to override default backend base URL.
  - Run: python scripts/prefetch_rozee.py --query "software engineer" --city pakistan --max-pages 2

This script uses the local scraper code to get jobs (so it behaves like your local environment).
"""

import os
import argparse
import requests
from scrapers.rozee_scraper import scrape_query

DEFAULT_BACKEND = os.environ.get('BACKEND_URL', 'https://backend-five-ruby-47.vercel.app')


def upsert_job(session: requests.Session, backend_base: str, job: dict):
    url = backend_base.rstrip('/') + '/jobs/upsert'
    payload = {
        'title': job.get('title'),
        'company': job.get('company'),
        'description': job.get('description'),
        'url': job.get('url'),
        'apply_url': job.get('apply_url'),
        'external_id': job.get('external_id'),
        'location': job.get('location') or job.get('city'),
        'city': job.get('city'),
        'salary': job.get('salary'),
        'posted_date': job.get('posted_date'),
        'source': job.get('source') or 'rozee',
    }
    resp = session.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--query', default='software engineer')
    parser.add_argument('--city', default=None)
    parser.add_argument('--max-pages', type=int, default=2)
    parser.add_argument('--backend', default=DEFAULT_BACKEND)
    args = parser.parse_args()

    print(f'Fetching Rozee jobs for query="{args.query}" city="{args.city}" max_pages={args.max_pages}')
    jobs = scrape_query(keyword=args.query, city=args.city, max_pages=args.max_pages)
    print(f'Fetched {len(jobs)} jobs from local Rozee scraper')

    session = requests.Session()
    session.headers.update({'User-Agent': 'prefetch-script/1.0'})

    upserted = 0
    for j in jobs:
        try:
            res = upsert_job(session, args.backend, j)
            upserted += 1
        except Exception as e:
            print('Failed to upsert:', e)
    print(f'Upserted {upserted} jobs to {args.backend}')


if __name__ == '__main__':
    main()
