"""Job API integrations with location-aware fallback behavior."""

from __future__ import annotations

import html
import os
import re
from typing import Dict, List, Optional, Tuple

import requests
import time
import concurrent.futures
import logging

# simple in-memory cache for recent search results
_search_cache: Dict[str, tuple] = {}
_logger = logging.getLogger(__name__)
_SEARCH_CACHE_TTL = 30
_SOURCE_TIMEOUT_SECONDS = max(4, int(os.getenv("SOURCE_TIMEOUT_SECONDS", "12")))

ADZUNA_BASE = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
REMOTIVE_URL = "https://remotive.com/api/remote-jobs"
JOBICY_URL = "https://jobicy.com/api/v2/remote-jobs"

HTML_TAG_RE = re.compile(r"<[^>]+>")

LOCATION_PRESETS: Dict[str, Tuple[Optional[str], str]] = {
    "pakistan": ("pk", ""),
    "karachi": ("pk", "Karachi"),
    "lahore": ("pk", "Lahore"),
    "islamabad": ("pk", "Islamabad"),
    "rawalpindi": ("pk", "Rawalpindi"),
    "faisalabad": ("pk", "Faisalabad"),
    "uae": ("ae", ""),
    "uk": ("gb", ""),
    "remote": (None, ""),
}

PAKISTAN_CITY_KEYS = {"karachi", "lahore", "islamabad", "rawalpindi", "faisalabad"}
REMOTE_SOURCES = {"remotive", "jobicy"}
QUERY_CORRECTIONS = {
    "artifical": "artificial",
    "artifical intelligence": "artificial intelligence",
    "machin learning": "machine learning",
}

# Explicit source registry so UI/API can explain why a source is not used.
PAKISTAN_SOURCE_STATUS: List[Dict[str, object]] = [
    {
        "key": "rozee",
        "active": True,
        "reason": "Primary Pakistan source with stable structured responses.",
    },
    {
        "key": "mustakbil",
        "active": True,
        "reason": "High-volume Pakistan listings with broad category coverage.",
    },
    {
        "key": "brightspyre",
        "active": True,
        "reason": "Pakistan tech board with targeted local openings.",
    },
    {
        "key": "bing_jobs",
        "active": True,
        "reason": "Search-index fallback that discovers jobs across multiple local sites.",
    },
    {
        "key": "google_indexed",
        "active": True,
        "reason": "DuckDuckGo-indexed discovery for broader local coverage.",
    },
    {
        "key": "linkedin",
        "active": True,
        "reason": "Indexed LinkedIn public job pages used as a supplemental source.",
    },
    {
        "key": "careers_page",
        "active": True,
        "reason": "Direct company careers pages for fresher first-party listings.",
    },
    {
        "key": "indeed",
        "active": False,
        "reason": "Intentionally disabled: aggressive anti-bot protections, frequent 403/rate limits, and high IP-block risk.",
    },
]


def clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = HTML_TAG_RE.sub(" ", str(value))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def get_pakistan_source_status() -> List[Dict[str, object]]:
    return list(PAKISTAN_SOURCE_STATUS)


def _resolve_country_and_where(location: str, city: Optional[str], country_code: str) -> Tuple[Optional[str], str]:
    city_value = (city or "").strip()
    location_value = (location or "").strip()

    if city_value:
        city_key = city_value.lower()
        if city_key in LOCATION_PRESETS:
            return LOCATION_PRESETS[city_key]
        return (country_code or "pk", city_value)

    if location_value:
        location_key = location_value.lower()
        if location_key in LOCATION_PRESETS:
            return LOCATION_PRESETS[location_key]
        return (country_code or "pk", location_value)

    return (country_code or "pk", "")


def _is_pakistan_city(location: str, city: Optional[str]) -> bool:
    city_key = (city or "").strip().lower()
    location_key = (location or "").strip().lower()
    return city_key in PAKISTAN_CITY_KEYS or location_key in PAKISTAN_CITY_KEYS


def _build_salary(item: Dict) -> str:
    salary = item.get("salary")
    if salary:
        return clean_text(str(salary))

    min_salary = item.get("salary_min")
    max_salary = item.get("salary_max")
    if min_salary is not None and max_salary is not None:
        return f"{min_salary}-{max_salary}"
    if min_salary is not None:
        return str(min_salary)
    if max_salary is not None:
        return str(max_salary)

    annual = item.get("annual_salary_min") or item.get("annual_salary_max")
    if annual is not None:
        return str(annual)

    return ""


def _normalize_job(item: Dict, source: str) -> Dict:
    company = item.get("company_name") or item.get("company") or ""
    if isinstance(company, dict):
        company = company.get("display_name") or company.get("name") or ""

    location = item.get("candidate_required_location") or item.get("location") or ""
    if isinstance(location, dict):
        location = location.get("display_name") or location.get("area") or ""

    external_id = item.get("external_id") or item.get("id") or item.get("job_id") or item.get("slug")
    normalized_url = str(
        item.get("redirect_url")
        or item.get("url")
        or item.get("apply_url")
        or item.get("job_url")
        or item.get("job_apply_url")
        or item.get("application_url")
        or item.get("link")
        or ""
    ).strip()

    if not normalized_url:
        external_url = str(external_id or "").strip()
        if external_url.startswith("http://") or external_url.startswith("https://"):
            normalized_url = external_url

    return {
        "external_id": str(external_id or f"{source}:{item.get('title', '')}:{company}"),
        "title": clean_text(str(item.get("title") or item.get("jobTitle") or item.get("position") or "")),
        "company": clean_text(str(company or "Unknown")),
        "location": clean_text(str(location or item.get("job_geo") or item.get("job_city") or "Remote")),
        "description": clean_text(
            str(item.get("description") or item.get("job_description") or item.get("snippet") or "")
        ),
        "url": normalized_url,
        "apply_url": normalized_url,
        "source": source,
        "salary": _build_salary(item),
        "posted_date": str(
            item.get("created")
            or item.get("publication_date")
            or item.get("date")
            or item.get("pubDate")
            or ""
        ),
    }


def fetch_adzuna(query: str, country_code: str = "pk", where: str = "", results_per_page: int = 20) -> List[Dict]:
    app_id = os.getenv("ADZUNA_APP_ID", "")
    app_key = os.getenv("ADZUNA_APP_KEY", "")
    if not app_id or not app_key:
        return []

    response = requests.get(
        ADZUNA_BASE.format(country=country_code.lower()),
        params={
            "app_id": app_id,
            "app_key": app_key,
            "what": query,
            "where": where,
            "results_per_page": results_per_page,
        },
        timeout=4,
    )
    response.raise_for_status()

    return [_normalize_job(item, "adzuna") for item in (response.json().get("results") or [])]


def fetch_remotive(query: str, limit: int = 20) -> List[Dict]:
    response = requests.get(
        REMOTIVE_URL,
        params={"search": query, "limit": limit},
        timeout=4,
    )
    response.raise_for_status()
    return [_normalize_job(item, "remotive") for item in (response.json().get("jobs") or [])]


def fetch_jobicy(query: str, count: int = 20) -> List[Dict]:
    response = requests.get(
        JOBICY_URL,
        params={"tag": query, "count": count},
        timeout=4,
    )
    response.raise_for_status()

    payload = response.json()
    jobs = payload.get("jobs") if isinstance(payload, dict) else payload
    return [_normalize_job(item, "jobicy") for item in (jobs or [])]


def _remote_candidate_filter(job: Dict) -> bool:
    description = clean_text(job.get("description", "")).lower()
    location = clean_text(job.get("location", "")).lower()

    in_description = ("pakistan" in description) or ("remote" in description)
    in_location = ("pakistan" in location) or ("remote" in location)
    return in_description or in_location


def _matches_query(job: Dict, query: str) -> bool:
    words = [word for word in re.findall(r"[a-z0-9+#.]+", (query or "").lower()) if len(word) > 2]
    if not words:
        return True
    searchable = f"{job.get('title', '')} {job.get('description', '')}".lower()
    return any(word in searchable for word in words)


def _normalize_query(query: str) -> str:
    normalized = (query or "").strip().lower()
    for wrong, right in QUERY_CORRECTIONS.items():
        normalized = re.sub(rf"\b{re.escape(wrong)}\b", right, normalized)
    return normalized


def _query_variants(query: str) -> List[str]:
    normalized = _normalize_query(query)
    variants = [normalized]
    if _is_ai_query(normalized):
        variants.extend(["ai engineer", "machine learning", "ai ml", "data science", "generative ai"])
    return list(dict.fromkeys([variant for variant in variants if variant]))


def _is_ai_query(query: str) -> bool:
    normalized = _normalize_query(query)
    return any(
        term in normalized
        for term in ["artificial intelligence", "ai engineer", " ai", "ai ", "machine learning", "data science", "generative ai"]
    )


def _title_contains_any(title: str, terms: List[str]) -> bool:
    title_lower = (title or "").lower()
    for term in terms:
        if len(term) <= 3:
            if re.search(rf"\b{re.escape(term)}\b", title_lower):
                return True
        elif term in title_lower:
            return True
    return False


def _matches_remote_title(job: Dict, query: str) -> bool:
    title = str(job.get("title") or "").lower()
    query_lower = _normalize_query(query)
    if not query_lower.strip():
        return True

    if _is_ai_query(query_lower):
        return _title_contains_any(
            title,
            [
                "ai",
                "artificial intelligence",
                "machine learning",
                "ml",
                "data science",
                "data scientist",
                "generative",
                "prompt engineer",
            ],
        )

    if "software engineer" in query_lower:
        software_role_terms = [
            "software",
            "developer",
            "devloper",
            "full-stack",
            "full stack",
            "backend",
            "frontend",
            "react",
            "python",
            "node",
            "programmer",
            "devops",
            "android",
            "ios",
            "qa",
            "quality assurance",
            "it support",
            "it helpdesk",
            "technical support",
        ]
        return any(term in title for term in software_role_terms)

    words = [word for word in re.findall(r"[a-z0-9+#.]+", query_lower) if len(word) > 2]
    return any(word in title for word in words)


def _filter_city(jobs: List[Dict], city: Optional[str]) -> List[Dict]:
    if not city:
        return jobs
    city_key = city.strip().lower()
    if city_key not in PAKISTAN_CITY_KEYS:
        return jobs
    filtered = []
    for job in jobs:
        location_key = clean_text(job.get("location") or job.get("city") or "").lower()
        if location_key == city_key:
            filtered.append(job)
    return filtered


def fetch_indexed_pakistan(query: str, city: str, max_urls: int = 4) -> List[Dict]:
    """Free fallback for Pakistan-local jobs when Adzuna has no data or no keys."""
    try:
        from scrapers.indexed_jobs_scraper import scrape_query
    except Exception:
        return []

    try:
        raw_jobs = scrape_query(keyword=query, city=city.lower(), max_urls=max_urls)
    except Exception:
        return []

    normalized = []
    for raw in raw_jobs:
        item = dict(raw)
        item["location"] = city
        item["source"] = item.get("source") or "google_indexed"
        normalized.append(_normalize_job(item, item["source"]))
    return [job for job in normalized if _matches_query(job, query)]


def fetch_rozee_pakistan(query: str, city: Optional[str] = None, max_pages: int = 1) -> List[Dict]:
    try:
        from scrapers.rozee_scraper import scrape_query
    except Exception:
        _logger.warning("Rozee scraper import failed")
        return []
    raw_jobs = []
    # quick availability check: if Rozee search page is blocked (Cloudflare), prefer indexed/Bing fallbacks
    try:
        import requests as _requests
        city_slug = (city or "pakistan").strip().lower().replace(" ", "-")
        query_slug = (query or "software engineer").strip().lower().replace(" ", "-")
        check_url = f"https://www.rozee.pk/search/{query_slug}-jobs-in-{city_slug}"
        _resp = _requests.get(check_url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        if _resp.status_code != 200 or ("Cloudflare" in (_resp.text or "") and _resp.status_code == 403):
            _logger.warning("Rozee appears blocked from this host: status=%s", _resp.status_code)
            # try indexed and bing fallbacks immediately
            try:
                indexed_jobs = fetch_indexed_pakistan(query=query, city=city or "pakistan", max_urls=10)
            except Exception:
                indexed_jobs = []
            try:
                bing_jobs = fetch_bing_pakistan(query=query, city=city, max_pages=1)
            except Exception:
                bing_jobs = []

            rozee_from_indexed = []
            for item in (indexed_jobs + bing_jobs):
                url = str(item.get("url") or "")
                if "rozee.pk" in url.lower():
                    item["source"] = "rozee"
                    rozee_from_indexed.append(_normalize_job(item, "rozee"))

            if rozee_from_indexed:
                return _filter_city(rozee_from_indexed, city)
            # otherwise continue to attempt normal scraping
    except Exception:
        pass
    for variant in _query_variants(query):
        try:
            _logger.info("Fetching Rozee variant '%s' (city=%s, pages=%s)", variant, city, max_pages)
            fetched = scrape_query(keyword=variant, city=city.lower() if city else None, max_pages=max_pages)
            _logger.info("Rozee fetched %d items for variant '%s'", len(fetched or []), variant)
            raw_jobs.extend(fetched or [])
        except Exception as exc:
            _logger.exception("Rozee fetch failed for variant '%s': %s", variant, exc)
            continue

    jobs = []
    for raw in raw_jobs:
        item = dict(raw)
        item["source"] = "rozee"
        item["location"] = item.get("location") or item.get("city") or city or "Pakistan"
        jobs.append(_normalize_job(item, "rozee"))

    filtered = [job for job in jobs if _matches_remote_title(job, query)]

    # Fallback: if direct Rozee scraping returns nothing in hosted environments,
    # pull Rozee URLs from indexed web results and normalize them as Rozee jobs.
    if not filtered:
        try:
            from scrapers.indexed_jobs_scraper import scrape_query as indexed_scrape_query

            fallback_city = city.lower() if city else "lahore"
            indexed_jobs = indexed_scrape_query(keyword=query, city=fallback_city, max_urls=8)
            fallback = []
            for raw in indexed_jobs:
                item = dict(raw)
                url = str(item.get("apply_url") or item.get("url") or "")
                if "rozee.pk" not in url.lower():
                    continue
                item["source"] = "rozee"
                item["location"] = item.get("location") or item.get("city") or city or "Pakistan"
                fallback.append(_normalize_job(item, "rozee"))

            if fallback:
                filtered = [job for job in fallback if _matches_remote_title(job, query)] or fallback
                _logger.info("Rozee fallback via indexed results produced %d jobs", len(filtered))
        except Exception as exc:
            _logger.warning("Rozee indexed fallback failed: %s", exc)

    if not filtered:
        city_slug = (city or "pakistan").strip().lower().replace(" ", "-")
        query_slug = (query or "software engineer").strip().lower().replace(" ", "-")
        rozee_search_url = f"https://www.rozee.pk/search/{query_slug}-jobs-in-{city_slug}"
        filtered = [
            {
                "external_id": rozee_search_url,
                "title": f"{query.title()} jobs on Rozee",
                "company": "Rozee.pk",
                "location": city or "Pakistan",
                "description": "Open Rozee search results for this query.",
                "url": rozee_search_url,
                "apply_url": rozee_search_url,
                "source": "rozee",
                "salary": "",
                "posted_date": "",
            }
        ]

    _logger.info("Rozee total normalized %d, filtered %d", len(jobs), len(filtered))
    # If Rozee appears to be blocked (only placeholder or very few results),
    # try extracting Rozee links from Bing search results as a stronger fallback.
    try:
        if len(filtered) <= 1:
            try:
                bing_jobs = fetch_bing_pakistan(query=query, city=city, max_pages=1)
                rozee_from_bing = []
                for item in bing_jobs:
                    url = str(item.get("url") or "")
                    if "rozee.pk" in url.lower():
                        item["source"] = "rozee"
                        rozee_from_bing.append(_normalize_job(item, "rozee"))
                if rozee_from_bing:
                    filtered = rozee_from_bing
                    _logger.info("Rozee recovered via Bing fallback %d jobs", len(filtered))
            except Exception as exc:
                _logger.warning("Rozee Bing fallback failed: %s", exc)
    except Exception:
        pass

    return _filter_city(filtered, city)


def fetch_mustakbil_pakistan(query: str, city: Optional[str] = None, max_pages: int = 1) -> List[Dict]:
    try:
        from scrapers.mustakbil_scraper import scrape_query
    except Exception:
        return []

    raw_jobs = []
    target_city = city.lower() if city else "lahore"
    
    # Mustakbil returns raw jobs; fetch from broad queries to get diverse job types.
    for variant in _query_variants(query):
        try:
            raw_jobs.extend(scrape_query(keyword=variant, city=target_city, max_pages=max_pages))
        except Exception:
            continue

    jobs = []
    for raw in raw_jobs:
        item = dict(raw)
        item["source"] = "mustakbil"
        item["location"] = item.get("location") or item.get("city") or city or "Pakistan"
        jobs.append(_normalize_job(item, "mustakbil"))
    
    # Don't over-filter Mustakbil: return all jobs for versatility.
    # (Other sources already apply query matching; Mustakbil shows raw catalog.)
    return _filter_city(jobs, city)


def fetch_bing_pakistan(query: str, city: Optional[str] = None, max_pages: int = 1) -> List[Dict]:
    """Fetch jobs from Bing search results for Pakistan job sites"""
    try:
        from scrapers.bing_scraper import scrape_query
    except Exception:
        return []

    raw_jobs = []
    for variant in _query_variants(query):
        try:
            raw_jobs.extend(scrape_query(keyword=variant, city=city.lower() if city else "lahore", max_pages=max_pages))
        except Exception:
            continue

    jobs = []
    for raw in raw_jobs:
        item = dict(raw)
        url_lower = str(item.get("url") or "").lower()
        if "rozee.pk" in url_lower:
            item["source"] = "rozee"
        elif "mustakbil.com" in url_lower:
            item["source"] = "mustakbil"
        elif "brightspyre.com" in url_lower:
            item["source"] = "brightspyre"
        else:
            item["source"] = "bing_jobs"
        item["location"] = item.get("location") or item.get("city") or city or "Pakistan"
        jobs.append(_normalize_job(item, item["source"]))
    return _filter_city([job for job in jobs if _matches_remote_title(job, query)], city)


def fetch_brightspyre(query: str, max_pages: int = 1) -> List[Dict]:
    """Fetch jobs from BrightSpyre job board"""
    try:
        from scrapers.brightspyre_scraper import scrape_query
    except Exception:
        return []

    raw_jobs = []
    for variant in _query_variants(query):
        try:
            raw_jobs.extend(scrape_query(keyword=variant, max_pages=max_pages))
        except Exception:
            continue

    jobs = []
    for raw in raw_jobs:
        item = dict(raw)
        item["source"] = "brightspyre"
        item["location"] = item.get("location") or item.get("city") or "Pakistan"
        jobs.append(_normalize_job(item, "brightspyre"))
    return [job for job in jobs if _matches_remote_title(job, query)]


def fetch_linkedin_indexed(query: str, city: Optional[str] = None, max_jobs: int = 4) -> List[Dict]:
    try:
        from scrapers.linkedin_indexed_scraper import scrape_query
    except Exception:
        return []

    raw_jobs = []
    target_city = city.lower() if city else "lahore"
    for variant in _query_variants(query):
        try:
            raw_jobs.extend(scrape_query(keyword=variant, city=target_city, max_jobs=max_jobs))
        except Exception:
            continue

    jobs = []
    for raw in raw_jobs:
        item = dict(raw)
        item["source"] = "linkedin"
        item["location"] = item.get("location") or item.get("city") or city or "Pakistan"
        jobs.append(_normalize_job(item, "linkedin"))
    return _filter_city([job for job in jobs if _matches_remote_title(job, query)], city)


def fetch_company_careers(query: str, company_limit: int = 6) -> List[Dict]:
    try:
        from backend.config.pakistan_jobs_config import PAKISTANI_COMPANIES
        from scrapers.careers_page_scraper import scrape_company
    except Exception:
        return []

    raw_jobs = []
    for company in PAKISTANI_COMPANIES[:company_limit]:
        try:
            raw_jobs.extend(scrape_company(company))
        except Exception:
            continue

    jobs = []
    for raw in raw_jobs:
        item = dict(raw)
        item["source"] = "careers_page"
        item["location"] = item.get("location") or item.get("city") or "Pakistan"
        jobs.append(_normalize_job(item, "careers_page"))
    return [job for job in jobs if _matches_remote_title(job, query)]


def _mark_remote(jobs: List[Dict]) -> List[Dict]:
    marked = []
    for job in jobs:
        j = dict(job)
        j["location"] = "Remote"
        marked.append(j)
    return marked


def dedupe_jobs(jobs: List[Dict]) -> List[Dict]:
    seen = set()
    unique: List[Dict] = []

    for job in jobs:
        key = job.get("external_id") or f"{job.get('title')}::{job.get('company')}::{job.get('url')}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(job)

    return unique


def _clean_jobs(jobs: List[Dict]) -> List[Dict]:
    for job in jobs:
        job["description"] = clean_text(job.get("description", ""))
    return jobs


def search_jobs(
    query: str,
    location: str = "Pakistan",
    city: Optional[str] = None,
    remote_only: bool = False,
    country_code: str = "pk",
    pakistan_only: bool = False,
    diagnostics: Optional[Dict] = None,
) -> List[Dict]:
    query = _normalize_query(query)
    location_key = (location or "").strip().lower()
    is_remote_mode = remote_only or location_key == "remote"
    cache_key = query

    # Simple in-memory cache to speed up repeated queries during active UI use
    try:
        if cache_key in _search_cache:
            ts, cached = _search_cache[cache_key]
            if time.time() - ts < _SEARCH_CACHE_TTL:
                return cached
    except Exception:
        pass

    def _collect_future(future: concurrent.futures.Future, source_name: str) -> List[Dict]:
        try:
            return future.result(timeout=_SOURCE_TIMEOUT_SECONDS)
        except concurrent.futures.TimeoutError:
            _logger.warning("search source timed out after %ss: %s", _SOURCE_TIMEOUT_SECONDS, source_name)
        except Exception as exc:
            _logger.warning("search source failed: %s (%s)", source_name, exc)
        return []

    # diagnostics helper
    def _record(source_name: str, count: int = 0, error: Optional[str] = None, elapsed: Optional[float] = None):
        if diagnostics is None:
            return
        try:
            diagnostics.setdefault("sources", {})
            diagnostics["query"] = query
            diagnostics["location"] = location
            diagnostics["city"] = city
            diagnostics["sources"][source_name] = {"count": int(count)}
            if error:
                diagnostics["sources"][source_name]["error"] = str(error)
            if elapsed is not None:
                diagnostics["sources"][source_name]["elapsed"] = float(elapsed)
        except Exception:
            pass

    # Remote-only mode: skip Adzuna entirely
    if is_remote_mode:
        remotive_jobs: List[Dict] = []
        jobicy_jobs: List[Dict] = []
        try:
            start = time.time()
            remotive_jobs = [job for job in fetch_remotive(query=query, limit=20) if _matches_remote_title(job, query)]
            _record("remotive", len(remotive_jobs), None, time.time() - start)
        except Exception:
            _record("remotive", 0, "failed")
            remotive_jobs = []

        try:
            start = time.time()
            jobicy_jobs = [job for job in fetch_jobicy(query=query, count=20) if _matches_remote_title(job, query)]
            _record("jobicy", len(jobicy_jobs), None, time.time() - start)
        except Exception:
            _record("jobicy", 0, "failed")
            jobicy_jobs = []

        return dedupe_jobs(_clean_jobs(_mark_remote(remotive_jobs + jobicy_jobs)))

    resolved_country, resolved_where = _resolve_country_and_where(location, city, country_code)
    country = resolved_country or (country_code or "pk")

    adzuna_city_jobs: List[Dict] = []
    adzuna_broad_jobs: List[Dict] = []
    remote_jobs: List[Dict] = []

    # City-specific behavior for Pakistan cities
    if _is_pakistan_city(location, city):
        try:
            adzuna_city_jobs = fetch_adzuna(query=query, country_code="pk", where=resolved_where or location, results_per_page=20)
            _record("adzuna_city", len(adzuna_city_jobs))
        except Exception:
            _record("adzuna_city", 0, "failed")
            adzuna_city_jobs = []

        try:
            adzuna_broad_jobs = fetch_adzuna(query=query, country_code="pk", where="", results_per_page=20)
            _record("adzuna_broad", len(adzuna_broad_jobs))
        except Exception:
            _record("adzuna_broad", 0, "failed")
            adzuna_broad_jobs = []

        # Fetch from all sources simultaneously for max results
        rozee_jobs = []
        indexed_jobs = []
        mustakbil_jobs = []
        bing_jobs = []
        linkedin_jobs = []
        careers_jobs = []
        
        # Run slower external fetches in parallel with a short per-call timeout
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=6)
        try:
            futures = {
                executor.submit(fetch_rozee_pakistan, query, resolved_where or location, 1): "rozee",
                # indexed fallback is expensive; run only if we need more results later
                # executor.submit(fetch_indexed_pakistan, query, resolved_where or location, 6): "indexed",
                executor.submit(fetch_mustakbil_pakistan, query, resolved_where or location, 1): "mustakbil",
                executor.submit(fetch_bing_pakistan, query, resolved_where or location, 1): "bing",
                executor.submit(fetch_linkedin_indexed, query, resolved_where or location, 4): "linkedin",
                executor.submit(fetch_company_careers, query, 6): "careers",
            }

            done, pending = concurrent.futures.wait(
                set(futures.keys()),
                timeout=_SOURCE_TIMEOUT_SECONDS,
                return_when=concurrent.futures.ALL_COMPLETED,
            )

            for fut in done:
                name = futures.get(fut, "unknown")
                try:
                    res = fut.result(timeout=0)
                except Exception as exc:
                    _logger.warning("search source failed: %s (%s)", name, exc)
                    _record(name, 0, str(exc))
                    res = []
                if name == "rozee":
                    rozee_jobs = res
                elif name == "mustakbil":
                    mustakbil_jobs = res
                elif name == "bing":
                    bing_jobs = res
                elif name == "linkedin":
                    linkedin_jobs = res
                elif name == "careers":
                    careers_jobs = res
                # record successful counts
                try:
                    _record(name, len(res or []))
                except Exception:
                    pass

            for fut in pending:
                _logger.warning("search source timed out after %ss: %s", _SOURCE_TIMEOUT_SECONDS, futures.get(fut, "unknown"))
                try:
                    _record(futures.get(fut, "unknown"), 0, "timed_out")
                except Exception:
                    pass
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        brightspyre_jobs = []
        try:
            brightspyre_jobs = fetch_brightspyre(query=query, max_pages=1)
        except Exception:
            pass

        combined_adzuna = dedupe_jobs(adzuna_city_jobs + adzuna_broad_jobs)
        # Try indexed fallback only if combined sources are low
        indexed_jobs = []
        all_sources = rozee_jobs + mustakbil_jobs + indexed_jobs + bing_jobs + linkedin_jobs + careers_jobs + brightspyre_jobs
        combined_adzuna = dedupe_jobs(combined_adzuna + all_sources)

        result = dedupe_jobs(_clean_jobs(combined_adzuna))
        if len(result) < 5:
            try:
                indexed_jobs = fetch_indexed_pakistan(query=query, city=resolved_where or location, max_urls=6)
                _record("indexed", len(indexed_jobs))
                combined_adzuna = dedupe_jobs(combined_adzuna + indexed_jobs)
                result = dedupe_jobs(_clean_jobs(combined_adzuna))
            except Exception:
                _record("indexed", 0, "failed")
                pass
        try:
            _search_cache[cache_key] = (time.time(), result)
        except Exception:
            pass
        return result

    # Pakistan (no city) or non-city location mode
    adzuna_jobs: List[Dict] = []
    try:
        adzuna_jobs = fetch_adzuna(query=query, country_code=country, where=resolved_where, results_per_page=20)
        _record("adzuna", len(adzuna_jobs))
    except Exception:
        _record("adzuna", 0, "failed")
        adzuna_jobs = []

    combined = list(adzuna_jobs)

    # Get jobs from all Pakistan sources simultaneously
    rozee_jobs = []
    mustakbil_jobs = []
    bing_jobs = []
    brightspyre_jobs = []
    linkedin_jobs = []
    careers_jobs = []
    
    if country.lower() == "pk":
        # Parallelize Pakistan-wide source fetches to reduce latency
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=6)
        try:
            futures = {
                executor.submit(fetch_rozee_pakistan, query, None, 1): "rozee",
                executor.submit(fetch_bing_pakistan, query, None, 1): "bing",
                executor.submit(fetch_mustakbil_pakistan, query, None, 1): "mustakbil",
                executor.submit(fetch_brightspyre, query, 1): "brightspyre",
                executor.submit(fetch_linkedin_indexed, query, resolved_where or city, 4): "linkedin",
                executor.submit(fetch_company_careers, query, 6): "careers",
            }

            done, pending = concurrent.futures.wait(
                set(futures.keys()),
                timeout=_SOURCE_TIMEOUT_SECONDS,
                return_when=concurrent.futures.ALL_COMPLETED,
            )

            for fut in done:
                name = futures.get(fut, "unknown")
                try:
                    res = fut.result(timeout=0)
                except Exception as exc:
                    _logger.warning("search source failed: %s (%s)", name, exc)
                    _record(name, 0, str(exc))
                    res = []
                if name == "rozee":
                    rozee_jobs = res
                elif name == "bing":
                    bing_jobs = res
                elif name == "mustakbil":
                    mustakbil_jobs = res
                elif name == "brightspyre":
                    brightspyre_jobs = res
                elif name == "linkedin":
                    linkedin_jobs = res
                elif name == "careers":
                    careers_jobs = res
                try:
                    _record(name, len(res or []))
                except Exception:
                    pass

            for fut in pending:
                _logger.warning("search source timed out after %ss: %s", _SOURCE_TIMEOUT_SECONDS, futures.get(fut, "unknown"))
                try:
                    _record(futures.get(fut, "unknown"), 0, "timed_out")
                except Exception:
                    pass
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

        combined.extend(rozee_jobs)
        combined.extend(mustakbil_jobs)
        combined.extend(bing_jobs)
        combined.extend(brightspyre_jobs)
        combined.extend(linkedin_jobs)
        combined.extend(careers_jobs)

        # cache the combined result briefly
        try:
            result = dedupe_jobs(_clean_jobs(combined))
            _search_cache[cache_key] = (time.time(), result)
        except Exception:
            result = dedupe_jobs(_clean_jobs(combined))

        return result

    if pakistan_only:
        return dedupe_jobs(_clean_jobs(combined))

    if country.lower() == "pk":
        return dedupe_jobs(_clean_jobs(combined))

    # standard fallback when both toggles are off
    if len(combined) < 5:
        try:
            remotive_jobs = [
                j for j in fetch_remotive(query=query, limit=20)
                if _remote_candidate_filter(j) and _matches_remote_title(j, query)
            ]
        except Exception:
            remotive_jobs = []
        combined.extend(_mark_remote(remotive_jobs))

    if len(dedupe_jobs(combined)) < 5:
        try:
            jobicy_jobs = [
                j for j in fetch_jobicy(query=query, count=20)
                if _remote_candidate_filter(j) and _matches_remote_title(j, query)
            ]
        except Exception:
            jobicy_jobs = []
        combined.extend(_mark_remote(jobicy_jobs))

    return dedupe_jobs(_clean_jobs(combined))
