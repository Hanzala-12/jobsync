from __future__ import annotations

from datetime import datetime
from typing import Dict, List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

from config.pakistan_jobs_config import CITIES, KEYWORDS
from scrapers.common import absolutize, normalize_and_store, request_html, soup_for, visible_text

SOURCE = "mustakbil"
BASE_URL = "https://www.mustakbil.com"


def scrape_query(keyword: str = "software engineer", city: str = "lahore", max_pages: int = 5) -> List[Dict]:
    jobs: List[Dict] = []
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/jobs/search/?q={quote_plus(keyword)}&city={quote_plus(city)}&page={page}"
        try:
            soup = soup_for(url)
        except Exception:
            break

        cards = soup.select(".job-listing, .job, article, .search-result, .job-row")
        if not cards:
            cards = soup.select("a[href*='/jobs/job/'], a[href*='/jobs/']")

        for card in cards[:20]:
            anchor = card if card.name == "a" else card.select_one("a[href]")
            href = anchor.get("href") if anchor else ""
            title = visible_text(anchor) or visible_text(card.select_one("h2, h3, .title"))
            if not title:
                continue
            apply_url = absolutize(BASE_URL, href)
            detail = _fetch_detail(apply_url)
            raw = {
                "title": title,
                "company": visible_text(card.select_one(".company, .company-name")) or detail.get("company", ""),
                "city": city,
                "salary": visible_text(card.select_one(".salary")) or detail.get("salary", ""),
                "job_type": visible_text(card.select_one(".job-type")),
                "experience": visible_text(card.select_one(".experience")),
                "posted_date": visible_text(card.select_one(".date, .posted")) or detail.get("posted_date"),
                "apply_url": apply_url,
                "description": detail.get("description", visible_text(card)),
                "possibly_inactive": _last_date_passed(detail.get("description", "")),
            }
            jobs.append(raw)
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
