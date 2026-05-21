from __future__ import annotations

from typing import Dict, List

from sqlalchemy.orm import Session

try:
    from config.pakistan_jobs_config import PAKISTANI_COMPANIES
except Exception:
    from backend.config.pakistan_jobs_config import PAKISTANI_COMPANIES
from scrapers.common import absolutize, normalize_and_store, soup_for, tech_job, visible_text

SOURCE = "careers_page"
CAREER_PATHS = ["/careers", "/jobs", "/open-positions", "/opportunities"]


def scrape_company(company: Dict) -> List[Dict]:
    jobs: List[Dict] = []
    urls = [company["careers_url"]]
    base = company["careers_url"].rstrip("/")
    root = "/".join(base.split("/")[:3])
    urls.extend(root + path for path in CAREER_PATHS)

    for url in dict.fromkeys(urls):
        try:
            soup = soup_for(url)
        except Exception:
            continue

        cards = soup.select("a[href*='job'], a[href*='career'], a[href*='position'], .job, .opening, .position, article")
        for card in cards[:25]:
            anchor = card if card.name == "a" else card.select_one("a[href]")
            title = visible_text(anchor) or visible_text(card.select_one("h2, h3, .title"))
            if not title:
                continue
            apply_url = absolutize(url, anchor.get("href") if anchor else url)
            raw = {
                "title": title,
                "company": company["name"],
                "city": visible_text(card.select_one(".location, [class*=location]")) or "pakistan",
                "salary": "",
                "job_type": visible_text(card.select_one(".type, [class*=type]")),
                "posted_date": visible_text(card.select_one(".date, [class*=date]")),
                "apply_url": apply_url,
                "description": visible_text(card),
            }
            if tech_job(raw):
                jobs.append(raw)
        if jobs:
            break
    return jobs


def run(db: Session, company_limit: int | None = None) -> List[Dict]:
    results = []
    for company in PAKISTANI_COMPANIES[: company_limit or len(PAKISTANI_COMPANIES)]:
        results.extend(normalize_and_store(db, scrape_company(company), SOURCE))
    return results


def run_sample(db: Session) -> List[Dict]:
    return normalize_and_store(db, scrape_company(PAKISTANI_COMPANIES[0])[:3], SOURCE)
