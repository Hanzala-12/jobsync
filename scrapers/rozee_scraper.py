from __future__ import annotations

import asyncio
from typing import Dict, List
from urllib.parse import quote_plus

from sqlalchemy.orm import Session

from config.pakistan_jobs_config import CITIES, KEYWORDS
from scrapers.common import detect_captcha, normalize_and_store, random_user_agent, sleep_between

SOURCE = "rozee"
BASE_URL = "https://www.rozee.pk"
CITY_CODES = {
    "karachi": 1,
    "lahore": 2,
    "islamabad": 4,
    "rawalpindi": 5,
    "peshawar": 14,
}


async def scrape_query_async(keyword: str = "software engineer", city: str = "lahore", max_pages: int = 5) -> List[Dict]:
    from playwright.async_api import async_playwright

    jobs: List[Dict] = []
    city_code = CITY_CODES.get(city)
    urls = []
    if city_code:
        urls.append(f"{BASE_URL}/job/jsearch/q/{quote_plus(keyword)}/fc/{city_code}")
    urls.append(f"{BASE_URL}/all/jobs/q-{quote_plus(keyword)}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(user_agent=random_user_agent())
        page = await context.new_page()
        try:
            for base_url in urls:
                for page_no in range(1, max_pages + 1):
                    url = f"{base_url}?page={page_no}"
                    await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                    content = await page.content()
                    if detect_captcha(content):
                        return jobs
                    cards = await page.query_selector_all(".job, .job-card, article, a[href*='/job-detail']")
                    for card in cards[:20]:
                        text = await card.inner_text()
                        anchor = await card.query_selector("a[href]")
                        href = await anchor.get_attribute("href") if anchor else url
                        title = (await anchor.inner_text()) if anchor else text.splitlines()[0] if text else ""
                        if not title:
                            continue
                        apply_url = href if href.startswith("http") else f"{BASE_URL}{href}"
                        description = await _fetch_description(page, apply_url)
                        jobs.append(
                            {
                                "title": title,
                                "company": _line_after(text, "Company") or "",
                                "city": city,
                                "salary": _line_after(text, "Salary") or "",
                                "job_type": _line_after(text, "Type") or "",
                                "experience": _line_after(text, "Experience") or "",
                                "posted_date": _line_after(text, "Posted") or "",
                                "apply_url": apply_url,
                                "description": description or text,
                            }
                        )
                    sleep_between(3, 7)
                sleep_between(5, 10)
        finally:
            await browser.close()
    return jobs


async def _fetch_description(page, url: str) -> str:
    try:
        detail = await page.context.new_page()
        await detail.goto(url, wait_until="domcontentloaded", timeout=30000)
        description = await detail.locator("body").inner_text(timeout=5000)
        await detail.close()
        return description
    except Exception:
        return ""


def _line_after(text: str, label: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    for index, line in enumerate(lines):
        if label.lower() in line.lower() and index + 1 < len(lines):
            return lines[index + 1]
    return ""


def scrape_query(keyword: str = "software engineer", city: str = "lahore", max_pages: int = 5) -> List[Dict]:
    try:
        return asyncio.run(scrape_query_async(keyword, city, max_pages))
    except RuntimeError:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(scrape_query_async(keyword, city, max_pages))


def run(db: Session, keyword_limit: int | None = None, city_limit: int | None = None) -> List[Dict]:
    results = []
    cities = [city for city in CITIES if city in CITY_CODES]
    for keyword in KEYWORDS[: keyword_limit or len(KEYWORDS)]:
        for city in cities[: city_limit or len(cities)]:
            results.extend(normalize_and_store(db, scrape_query(keyword, city), SOURCE))
    return results


def run_sample(db: Session) -> List[Dict]:
    return normalize_and_store(db, scrape_query("software engineer", "lahore", max_pages=1)[:3], SOURCE)
