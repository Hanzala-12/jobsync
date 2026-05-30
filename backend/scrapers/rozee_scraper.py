from __future__ import annotations

import json
import re
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session

try:
    from config.pakistan_jobs_config import CITIES, KEYWORDS
except Exception:
    from backend.config.pakistan_jobs_config import CITIES, KEYWORDS
from scrapers.common import normalize_and_store

SOURCE = "rozee"
BASE_URL = "https://www.rozee.pk"
ROZEE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")


def _url_for(keyword: str, city: Optional[str] = None, page: int = 1) -> str:
    if city:
        path = f"/search/{_slug(keyword)}-jobs-in-{_slug(city)}"
    else:
        path = f"/job/jsearch/q/{quote_plus(keyword)}"

    if page <= 1:
        return f"{BASE_URL}{path}"
    return f"{BASE_URL}{path}/pg/{page}"


def _extract_ap_resp(html: str) -> Dict:
    # Match more flexibly: allow optional "var" or "window." prefixes
    match = re.search(r"(?:var\s+|window\.)?apResp\s*=\s*", html)
    if not match:
        return {}

    # Find the first JSON object start after the match (skip whitespace)
    start = match.end()
    # advance to the next '{'
    while start < len(html) and html[start].isspace():
        start += 1
    if start >= len(html) or html[start] != "{":
        return {}

    depth = 0
    in_string = False
    escaped = False
    for index, char in enumerate(html[start:], start):
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[start : index + 1])
                except json.JSONDecodeError:
                    return {}
    return {}


def _city_from_job(item: Dict, fallback_city: Optional[str]) -> str:
    cities = item.get("city_exact") or []
    if isinstance(cities, list) and cities:
        return str(cities[0])
    if isinstance(cities, str) and cities:
        return cities
    return fallback_city or "Pakistan"


def _salary_from_job(item: Dict) -> str:
    salary = item.get("salaryTHide_exact_g") or item.get("salary") or ""
    if salary:
        return str(salary)
    min_salary = item.get("min_salary") or item.get("salaryMin")
    max_salary = item.get("max_salary") or item.get("salaryMax")
    if min_salary and max_salary:
        return f"PKR {min_salary} - {max_salary}"
    return ""


def _job_from_rozee_item(item: Dict, fallback_city: Optional[str]) -> Dict:
    city = _city_from_job(item, fallback_city)
    perma = item.get("rozeePermaLink") or ""
    apply_url = f"{BASE_URL}/{perma}" if perma and not perma.startswith("http") else perma

    return {
        "external_id": f"rozee:{item.get('jid') or perma}",
        "title": item.get("title") or item.get("title_exact") or "",
        "company": item.get("company_name") or item.get("company_exact") or "Rozee Employer",
        "city": city,
        "location": city,
        "salary": _salary_from_job(item),
        "job_type": item.get("type") or item.get("type_exact") or "",
        "experience": item.get("experience") or item.get("experience_exact") or "",
        "posted_date": item.get("created") or item.get("displayDate") or "",
        "apply_url": apply_url,
        "url": apply_url,
        "description": item.get("description_raw") or item.get("description") or "",
        "source": SOURCE,
    }


def scrape_query(keyword: str = "software engineer", city: Optional[str] = "lahore", max_pages: int = 2) -> List[Dict]:
    jobs: List[Dict] = []
    session = requests.Session()
    session.headers.update({"User-Agent": ROZEE_USER_AGENT, "Accept-Language": "en-US,en;q=0.9"})

    for page in range(1, max_pages + 1):
        url = _url_for(keyword, city, page)
        try:
            response = session.get(url, timeout=10)
            response.raise_for_status()
        except requests.RequestException:
            break

        payload = _extract_ap_resp(response.text)
        response_data = payload.get("response") or {}
        rozee_jobs = (response_data.get("jobs") or {}).get("basic") or []
        if not rozee_jobs:
            rozee_jobs = _extract_html_jobs(response.text, fallback_city=city)
        if not rozee_jobs:
            break

        for item in rozee_jobs:
            if item.get("source") == SOURCE and item.get("url"):
                jobs.append(item)
            else:
                jobs.append(_job_from_rozee_item(item, city))

    return jobs


def _extract_html_jobs(html: str, fallback_city: Optional[str]) -> List[Dict]:
    """Fallback parser when apResp JSON is unavailable (anti-bot or layout changes)."""
    soup = BeautifulSoup(html, "lxml")
    jobs: List[Dict] = []
    seen = set()

    for anchor in soup.select("a[href]"):
        href = (anchor.get("href") or "").strip()
        if "-jobs-" not in href:
            continue
        url = f"{BASE_URL}{href}" if href.startswith("/") else href
        if not url.startswith("http"):
            continue
        if "rozee.pk" not in url:
            continue
        if url in seen:
            continue
        seen.add(url)

        title = (anchor.get_text(" ", strip=True) or "").strip()
        if not title or len(title) < 3:
            continue

        jobs.append(
            {
                "external_id": url,
                "title": title,
                "company": "Rozee Employer",
                "city": fallback_city or "Pakistan",
                "location": fallback_city or "Pakistan",
                "salary": "",
                "job_type": "",
                "experience": "",
                "posted_date": "",
                "apply_url": url,
                "url": url,
                "description": "",
                "source": SOURCE,
            }
        )

        if len(jobs) >= 20:
            break

    return jobs


def run(db: Session, keyword_limit: int | None = None, city_limit: int | None = None) -> List[Dict]:
    results = []
    for keyword in KEYWORDS[: keyword_limit or len(KEYWORDS)]:
        for city in CITIES[: city_limit or len(CITIES)]:
            results.extend(normalize_and_store(db, scrape_query(keyword, city), SOURCE))
    return results


def run_sample(db: Session) -> List[Dict]:
    return normalize_and_store(db, scrape_query("software engineer", "lahore", max_pages=1)[:3], SOURCE)
