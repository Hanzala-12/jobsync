from __future__ import annotations

from typing import Dict, List
from urllib.parse import parse_qs, quote_plus, unquote, urlparse

from sqlalchemy.orm import Session

from config.pakistan_jobs_config import CITIES, KEYWORDS
from scrapers.common import normalize_and_store, request_html, soup_for, tech_job, visible_text

SOURCE = "google_indexed"
DUCK_URL = "https://html.duckduckgo.com/html/?q={query}"


def scrape_query(keyword: str = "software engineer", city: str = "lahore", max_urls: int = 5) -> List[Dict]:
    queries = [
        f'site:rozee.pk "{keyword}" "{city}"',
        f'site:mustakbil.com "{keyword}" "{city}"',
        f'"{keyword}" "apply now" "{city}" site:.pk',
    ]
    jobs: List[Dict] = []
    for search in queries:
        try:
            soup = soup_for(DUCK_URL.format(query=quote_plus(search)))
        except Exception:
            continue
        urls = []
        for anchor in soup.select("a[href]"):
            href = _extract_duck_url(anchor.get("href", ""))
            if href.startswith("http") and href not in urls:
                urls.append(href)
            if len(urls) >= max_urls:
                break
        for url in urls:
            raw = _extract_job_from_url(url, keyword, city)
            if raw and tech_job(raw):
                jobs.append(raw)
    return jobs


def _extract_job_from_url(url: str, keyword: str, city: str) -> Dict:
    try:
        html = request_html(url)
    except Exception:
        return {}
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "lxml")
    title = visible_text(soup.select_one("h1, h2, title")) or keyword
    company = visible_text(soup.select_one(".company, [class*=company], [itemprop*=hiringOrganization]")) or "Indexed Employer"
    description = visible_text(soup.select_one(".job-description, .description, article, main")) or visible_text(soup.body)
    return {
        "title": title,
        "company": company,
        "city": city,
        "apply_url": url,
        "description": description,
        "posted_date": visible_text(soup.select_one("time, .date, [class*=posted]")),
    }


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
    return normalize_and_store(db, scrape_query("software engineer", "lahore", max_urls=3)[:3], SOURCE)
