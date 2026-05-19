from __future__ import annotations

from typing import Dict, List
from urllib.parse import quote_plus

from sqlalchemy.orm import Session

from config.pakistan_jobs_config import KEYWORDS
from scrapers.common import absolutize, normalize_and_store, soup_for, tech_job, visible_text

SOURCE = "brightspyre"
BASE_URL = "https://www.brightspyre.com"


def scrape_query(keyword: str = "software engineer", max_pages: int = 5) -> List[Dict]:
    jobs: List[Dict] = []
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}/jobs?search={quote_plus(keyword)}&page={page}"
        try:
            soup = soup_for(url)
        except Exception:
            break

        cards = soup.select(".job, .job-item, article, .card, a[href*='/jobs/']")
        for card in cards[:20]:
            anchor = card if card.name == "a" else card.select_one("a[href]")
            href = anchor.get("href") if anchor else ""
            title = visible_text(anchor) or visible_text(card.select_one("h2, h3, .title"))
            if not title:
                continue
            raw = {
                "title": title,
                "company": visible_text(card.select_one(".company, [class*=company]")) or "BrightSpyre Employer",
                "city": visible_text(card.select_one(".location, [class*=location]")) or "pakistan",
                "salary": visible_text(card.select_one(".salary, [class*=salary]")),
                "job_type": visible_text(card.select_one(".type, [class*=type]")),
                "posted_date": visible_text(card.select_one(".date, [class*=date]")),
                "apply_url": absolutize(BASE_URL, href),
                "description": visible_text(card),
            }
            if tech_job(raw):
                jobs.append(raw)
    return jobs


def run(db: Session, keyword_limit: int | None = None) -> List[Dict]:
    results = []
    for keyword in KEYWORDS[: keyword_limit or len(KEYWORDS)]:
        results.extend(normalize_and_store(db, scrape_query(keyword), SOURCE))
    return results


def run_sample(db: Session) -> List[Dict]:
    return normalize_and_store(db, scrape_query("software engineer", max_pages=1)[:3], SOURCE)
