from __future__ import annotations

from datetime import datetime
from typing import Dict, List

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

try:
    from config.pakistan_jobs_config import CITIES, KEYWORDS
except Exception:
    from backend.config.pakistan_jobs_config import CITIES, KEYWORDS
from scrapers.common import absolutize, normalize_and_store, request_html, soup_for, visible_text

SOURCE = "mustakbil"
BASE_URL = "https://www.mustakbil.com"


def scrape_query(keyword: str = "software engineer", city: str = "lahore", max_pages: int = 5) -> List[Dict]:
    """Scrape Mustakbil listings. Returns ALL job types regardless of keyword query."""
    normalized_city = (city or "lahore").strip().lower()

    listing_urls = [
        f"{BASE_URL}/jobs/pakistan/{normalized_city}/information-technology",
        f"{BASE_URL}/jobs/pakistan/{normalized_city}",
    ]

    # Wider fallback for non-city searches or sparse city pages.
    if normalized_city in {"", "pakistan", "remote"}:
        listing_urls.extend(
            [
                f"{BASE_URL}/jobs/pakistan/information-technology",
                f"{BASE_URL}/jobs/pakistan",
            ]
        )

    jobs: List[Dict] = []
    seen_urls = set()

    for url in listing_urls:
        try:
            soup = soup_for(url)
        except Exception:
            continue

        # Mustakbil listing pages expose job links directly using /jobs/job/<id>
        links = soup.select("a[href*='/jobs/job/']")
        for anchor in links:
            href = anchor.get("href") or ""
            apply_url = absolutize(BASE_URL, href)
            if not apply_url or apply_url in seen_urls:
                continue

            title = visible_text(anchor)
            if not title or title.lower().startswith("view"):
                continue

            detail = _fetch_detail(apply_url)
            
            # Include all jobs from Mustakbil - don't filter by keyword.
            # User can search/filter later; we return raw data.
            seen_urls.add(apply_url)
            jobs.append(
                {
                    "title": title,
                    "company": detail.get("company", ""),
                    "city": normalized_city,
                    "salary": detail.get("salary", ""),
                    "job_type": "",
                    "experience": "",
                    "posted_date": detail.get("posted_date"),
                    "apply_url": apply_url,
                    "description": detail.get("description", ""),
                    "possibly_inactive": _last_date_passed(detail.get("description", "")),
                }
            )

            # Keep a reasonable cap per listing page to avoid slow full crawls.
            if len(jobs) >= 25:
                break

        if jobs:
            break

    return jobs


def _fetch_detail(url: str) -> Dict:
    try:
        html = request_html(url)
    except Exception:
        return {}
    soup = BeautifulSoup(html, "lxml")
    return {
        "company": visible_text(soup.select_one(".company, .company-name, [class*=company]")),
        "salary": visible_text(soup.select_one(".salary, [class*=salary]")),
        "posted_date": visible_text(soup.select_one(".date, .posted, [class*=posted]")),
        "description": visible_text(soup.select_one(".job-description, .description, [class*=description], main")) or visible_text(soup.body),
    }


def _last_date_passed(text: str) -> bool:
    import re

    match = re.search(r"last date(?: to apply)?[:\s]+(\d{1,2}\s+\w+\s+\d{4}|\d{4}-\d{2}-\d{2})", text, re.I)
    if not match:
        return False
    for fmt in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(match.group(1), fmt) < datetime.now()
        except ValueError:
            pass
    return False


def run(db: Session, keyword_limit: int | None = None, city_limit: int | None = None) -> List[Dict]:
    results = []
    for keyword in KEYWORDS[: keyword_limit or len(KEYWORDS)]:
        for city in CITIES[: city_limit or len(CITIES)]:
            results.extend(normalize_and_store(db, scrape_query(keyword, city), SOURCE))
    return results


def run_sample(db: Session) -> List[Dict]:
    return normalize_and_store(db, scrape_query("software engineer", "lahore", max_pages=1)[:3], SOURCE)
