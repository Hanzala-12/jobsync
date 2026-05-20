from __future__ import annotations

from typing import Dict, List
from urllib.parse import quote_plus

from bs4 import BeautifulSoup

from config.pakistan_jobs_config import CITIES, KEYWORDS
from scrapers.common import normalize_and_store, request_html, tech_job, visible_text

SOURCE = "bing_jobs"
BING_URL = "https://www.bing.com/search?q={query}"


def scrape_query(keyword: str = "software engineer", city: str = "lahore", max_pages: int = 2) -> List[Dict]:
    """Scrape job listings from Bing search results for Pakistani job sites"""
    jobs: List[Dict] = []
    
    # Search queries targeting Pakistan job sites
    queries = [
        f'site:mustakbil.com "{keyword}" "{city}"',
        f'site:rozee.pk "{keyword}" "{city}"',
        f'site:brightspyre.com "{keyword}" "{city}"',
        f'site:paperpk.com "{keyword}" "{city}"',
        f'site:mustakbil.com {keyword} jobs',
        f'site:rozee.pk {keyword} jobs',
        f'site:brightspyre.com {keyword} jobs',
        f'site:paperpk.com {keyword} jobs',
        f"{keyword} jobs in {city} pakistan",
        f"{keyword} careers {city}",
    ]
    seen_urls = set()
    
    for search_query in queries:
        for page in range(1, max_pages + 1):
            try:
                url = BING_URL.format(query=quote_plus(search_query))
                if page > 1:
                    url += f"&first={(page - 1) * 10}"
                
                html = request_html(url)
                soup = BeautifulSoup(html, "lxml")
                
                # Extract job links from Bing results
                for result in soup.select(".b_algo"):
                    link = result.select_one("h2 a")
                    if not link:
                        continue
                    
                    href = link.get("href", "")
                    title = visible_text(link)
                    snippet = visible_text(result.select_one(".b_caption"))
                    
                    if not href or not title:
                        continue
                    
                    # Filter for actual job pages
                    if _is_job_url(href) and href not in seen_urls:
                        seen_urls.add(href)
                        raw_job = _extract_job_info(href, title, snippet, keyword, city)
                        if raw_job and tech_job(raw_job):
                            jobs.append(raw_job)
                            
            except Exception:
                continue
    return jobs[:20]  # Return max 20 jobs


def _is_job_url(url: str) -> bool:
    """Check if URL likely contains a job posting"""
    if not url.startswith("http"):
        return False
    
    # Exclude bad URLs
    bad_keywords = ["kaggle", "github", "stackoverflow", "reddit", "medium", "youtube", "twitter", "redirect", "login", "sign"]
    url_lower = url.lower()
    if any(bad in url_lower for bad in bad_keywords):
        return False
    
    job_keywords = [
        "job", "career", "position", "vacancy", "recruit",
        "apply", "hiring", "opportunity", "openings",
        "/jobs/", "/careers/", "/vacancy", "/career/", "/positions/",
        "employment", "work", "hiring"
    ]
    
    return any(keyword in url_lower for keyword in job_keywords)


def _extract_job_info(url: str, title: str, snippet: str, keyword: str, city: str) -> Dict:
    """Extract job information from URL and snippet"""
    try:
        html = request_html(url)
    except Exception:
        return {}
    
    soup = BeautifulSoup(html, "lxml")
    
    # Remove script and style elements
    for script in soup(["script", "style"]):
        script.decompose()
    
    # Extract job details
    page_title = visible_text(soup.select_one("h1")) or title
    company_name = _extract_company_from_page(soup, url)
    description = visible_text(soup.select_one(".job-description, .description, [class*=description], main"))
    
    # Fallback to page text if no description found
    if not description:
        text = visible_text(soup.body) if soup.body else ""
        description = text[:1000] if text else snippet
    
    salary = visible_text(soup.select_one(".salary, [class*=salary]")) or _extract_salary_from_text(description)
    
    return {
        "title": page_title or keyword,
        "company": company_name or "Unknown",
        "city": city,
        "location": city,
        "salary": salary,
        "description": description,
        "url": url,
        "apply_url": url,
        "source": SOURCE,
        "posted_date": "",
    }


def _extract_company_from_page(soup: BeautifulSoup, url: str) -> str:
    """Extract company name from page"""
    # Try common company selectors
    company = visible_text(soup.select_one(
        "[itemprop='hiringOrganization'] [itemprop='name'], "
        "[class*=company], [class*=employer], "
        ".company-name, .employer-name, "
        "[data-company], [data-employer]"
    ))
    
    if company:
        return company
    
    # Fallback: extract from URL domain
    if "rozee" in url:
        return "Rozee.pk"
    elif "mustakbil" in url:
        return "Mustakbil"
    elif "brightspyre" in url:
        return "BrightSpyre"
    elif "paperpk" in url:
        return "PaperPk"
    elif "linkedin" in url:
        return "LinkedIn"
    
    return ""


def _extract_salary_from_text(text: str) -> str:
    """Extract salary information from text"""
    import re
    
    patterns = [
        r"(?:PKR|Rs\.?|Rupees?)\s*[\d,]+(?:\s*-\s*[\d,]+)?",
        r"(?:USD|$)\s*[\d,]+(?:\s*-\s*[\d,]+)?",
        r"[\d,]+\s*(?:PKR|Rs\.?|USD|$)",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0)
    
    return ""


def run(db, keyword_limit: int | None = None, city_limit: int | None = None) -> List[Dict]:
    """Run scraper for all keywords and cities"""
    results = []
    for keyword in KEYWORDS[: keyword_limit or len(KEYWORDS)]:
        for city in CITIES[: city_limit or len(CITIES)]:
            try:
                results.extend(normalize_and_store(db, scrape_query(keyword, city, max_pages=1)[:3], SOURCE))
            except Exception:
                continue
    return results


def run_sample(db) -> List[Dict]:
    """Run scraper with sample data"""
    return normalize_and_store(db, scrape_query("software engineer", "lahore", max_pages=1)[:3], SOURCE)
