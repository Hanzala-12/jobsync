from __future__ import annotations

from typing import Dict, List
from urllib.parse import quote_plus, unquote, urlparse, parse_qs

from sqlalchemy.orm import Session

from config.pakistan_jobs_config import CITIES, KEYWORDS
from scrapers.common import normalize_and_store, request_html, soup_for, visible_text

SOURCE = "linkedin"
DUCK_URL = "https://html.duckduckgo.com/html/?q={query}"


def scrape_query(keyword: str = "software engineer", city: str = "lahore", max_jobs: int = 5) -> List[Dict]:
    search = f"site:linkedin.com/jobs/view {keyword} {city} pakistan"
    try:
        soup = soup_for(DUCK_URL.format(query=quote_plus(search)))
    except Exception:
        return []

    urls = []
    for anchor in soup.select("a[href]"):
        href = _extract_duck_url(anchor.get("href", ""))
        if "linkedin.com/jobs/view" in href and href not in urls:
            urls.append(href)
        if len(urls) >= max_jobs:
            break

    jobs = []
    for url in urls:
        try:
            html = request_html(url)
        except Exception:
            continue
        if "authwall" in html.lower() or "login" in html.lower() and "linkedin" in html.lower():
            break
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "lxml")
        title = visible_text(soup.select_one("h1, .top-card-layout__title"))
        company = visible_text(soup.select_one(".topcard__org-name-link, .top-card-layout__card .topcard__flavor"))
        location = visible_text(soup.select_one(".topcard__flavor--bullet, .top-card-layout__second-subline"))
        description = visible_text(soup.select_one(".description, .show-more-less-html"))
        if title:
            jobs.append(
                {
                    "title": title,
                    "company": company or "LinkedIn Employer",
                    "city": city if city in location.lower() else location or city,
                    "apply_url": url,
                    "description": description,
                    "posted_date": visible_text(soup.select_one("time")),
                }
            )
    return jobs


def _extract_duck_url(href: str) -> str:
    if "uddg=" in href:
        parsed = urlparse(href)
        return unquote(parse_qs(parsed.query).get("uddg", [""])[0])
    return href


def run(db: Session, max_queries: int = 10) -> List[Dict]:
    results = []
    count = 0
    for keyword in KEYWORDS:
        for city in CITIES:
            if count >= max_queries:
                return results
            results.extend(normalize_and_store(db, scrape_query(keyword, city), SOURCE))
            count += 1
    return results


def run_sample(db: Session) -> List[Dict]:
    return normalize_and_store(db, scrape_query("software engineer", "lahore", max_jobs=3), SOURCE)
