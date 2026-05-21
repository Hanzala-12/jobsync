from __future__ import annotations

import random
import time
from typing import Dict, List
from urllib.parse import quote_plus

from scrapers.common import visible_text

SOURCE = "indeed"
BASE_URL = "https://pk.indeed.com"

# Rate limiting to avoid bans - Indeed is strict, so use longer delays
REQUEST_DELAY_MIN = 4.0  # Minimum 4 seconds between requests
REQUEST_DELAY_MAX = 10.0  # Maximum 10 seconds between requests
LAST_REQUEST_TIME = 0


def _get_browser_headers() -> Dict[str, str]:
    """Return realistic browser headers."""
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    return {"User-Agent": random.choice(user_agents)}


def _rate_limit():
    """Enforce rate limiting with human-like random delays."""
    global LAST_REQUEST_TIME
    elapsed = time.time() - LAST_REQUEST_TIME
    if elapsed < REQUEST_DELAY_MIN:
        sleep_time = random.uniform(REQUEST_DELAY_MIN, REQUEST_DELAY_MAX) - elapsed
        if sleep_time > 0:
            print(f"[indeed] Rate limiting: sleeping {sleep_time:.1f}s...")
            time.sleep(sleep_time)
    LAST_REQUEST_TIME = time.time()


def scrape_query(keyword: str = "software engineer", city: str = "lahore", max_pages: int = 1) -> List[Dict]:
    """
    Scrape Indeed Pakistan using Playwright to handle JavaScript rendering.
    Uses rate limiting to avoid bans.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[indeed] Playwright not installed - skipping Indeed scraper")
        return []
    
    jobs: List[Dict] = []
    
    try:
        with sync_playwright() as p:
            # Launch browser with stealth settings
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-web-resources",
                    "--disable-client-side-phishing-detection",
                ]
            )
            
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                ]),
            )
            
            # Add referer to look more human
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => false})")
            
            page = context.new_page()
            
            for page_num in range(max_pages):
                # Rate limit before each request
                if page_num > 0:
                    _rate_limit()
                else:
                    # Initial delay to appear more human
                    time.sleep(random.uniform(2, 3))
                
                start = page_num * 10
                url = f"{BASE_URL}/jobs?q={quote_plus(keyword)}&l={quote_plus(city)}&start={start}"
                
                print(f"[indeed] Fetching page {page_num}: {url}")
                
                try:
                    # Navigate with good timeout
                    page.goto(url, wait_until="networkidle", timeout=60000)
                    
                    # Wait for job listings to appear
                    try:
                        page.wait_for_selector("div[data-job-id], div.base-card", timeout=15000)
                    except:
                        print(f"[indeed] No job selector found - trying alternative selectors")
                    
                    # Get rendered HTML
                    html = page.content()
                    
                except Exception as e:
                    print(f"[indeed] Navigation error on page {page_num}: {e}")
                    break
                
                # Parse with BeautifulSoup
                try:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(html, "lxml")
                except Exception as e:
                    print(f"[indeed] Parse error: {e}")
                    break
                
                # Find job cards
                job_cards = soup.select("div[data-job-id], div.base-card, li.result-item")
                
                if not job_cards:
                    print(f"[indeed] No job cards found on page {page_num}")
                    break
                
                print(f"[indeed] Found {len(job_cards)} job cards")
                
                for card in job_cards:
                    try:
                        # Title - try multiple selectors
                        title_elem = card.select_one("h2 a, span[role='heading'], .jobTitle, a.jcs-JobTitle")
                        title = visible_text(title_elem) if title_elem else ""
                        if not title:
                            continue
                        
                        # Company
                        company_elem = card.select_one(
                            "div[data-company-name], span[data-company-name], .company"
                        )
                        company = visible_text(company_elem) if company_elem else "Indeed"
                        
                        # Location
                        location_elem = card.select_one(
                            "div[data-location], .location, span.compactLocation"
                        )
                        location = visible_text(location_elem) if location_elem else city
                        
                        # Job URL - data-jk attribute is job key
                        job_key = card.get("data-job-id") or card.get("data-jk")
                        if job_key:
                            job_url = f"{BASE_URL}/viewjob?jk={job_key}"
                        else:
                            url_elem = card.select_one("a[href*='/viewjob'], a[href*='/jobs/']")
                            if url_elem:
                                href = url_elem.get("href", "")
                                job_url = href if href.startswith("http") else BASE_URL + href
                            else:
                                continue
                        
                        # Salary
                        salary_elem = card.select_one("span[aria-label*='salary'], .salary-snippet")
                        salary = visible_text(salary_elem) if salary_elem else ""
                        
                        # Description
                        snippet_elem = card.select_one(".job-snippet, .snippet, .summary")
                        description = visible_text(snippet_elem) if snippet_elem else ""
                        
                        # Posted date
                        date_elem = card.select_one("span.date, time")
                        posted_date = visible_text(date_elem) if date_elem else ""
                        
                        if not title:
                            continue
                        
                        job = {
                            "title": title.strip(),
                            "company": company.strip(),
                            "city": location.strip(),
                            "salary": salary.strip(),
                            "job_type": "",
                            "posted_date": posted_date.strip(),
                            "apply_url": job_url,
                            "description": description.strip(),
                        }
                        
                        jobs.append(job)
                        print(f"[indeed]   ✓ {title[:60]}")
                        
                    except Exception as e:
                        print(f"[indeed] Error parsing card: {e}")
                        continue
                
                # Break if we found fewer than 10 on this page (likely last page)
                page_jobs = len(jobs) - (page_num * 10)
                if page_jobs < 10:
                    print(f"[indeed] Got fewer jobs than expected on page {page_num}, stopping")
                    break
            
            browser.close()
    
    except Exception as e:
        print(f"[indeed] Scraper error: {e}")
        import traceback
        traceback.print_exc()
    
    return jobs


if __name__ == "__main__":
    print("Testing Indeed Pakistan scraper...")
    jobs = scrape_query("python developer", "lahore", max_pages=1)
    print(f"\nFound {len(jobs)} jobs:")
    for job in jobs[:5]:
        print(f"  - {job['title']} @ {job['company']}")
