"""Job API integrations with location-aware fallback behavior."""

from __future__ import annotations

import html
import os
import re
from typing import Dict, List, Optional, Tuple

import requests

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


def clean_text(value: Optional[str]) -> str:
    if not value:
        return ""
    text = HTML_TAG_RE.sub(" ", str(value))
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


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

    external_id = item.get("id") or item.get("job_id") or item.get("slug")

    return {
        "external_id": str(external_id or f"{source}:{item.get('title', '')}:{company}"),
        "title": clean_text(str(item.get("title") or item.get("jobTitle") or item.get("position") or "")),
        "company": clean_text(str(company or "Unknown")),
        "location": clean_text(str(location or item.get("job_geo") or item.get("job_city") or "Remote")),
        "description": clean_text(
            str(item.get("description") or item.get("job_description") or item.get("snippet") or "")
        ),
        "url": str(
            item.get("redirect_url")
            or item.get("url")
            or item.get("job_url")
            or item.get("job_apply_url")
            or item.get("application_url")
            or ""
        ),
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
        timeout=20,
    )
    response.raise_for_status()

    return [_normalize_job(item, "adzuna") for item in (response.json().get("results") or [])]


def fetch_remotive(query: str, limit: int = 20) -> List[Dict]:
    response = requests.get(
        REMOTIVE_URL,
        params={"search": query, "limit": limit},
        timeout=20,
    )
    response.raise_for_status()
    return [_normalize_job(item, "remotive") for item in (response.json().get("jobs") or [])]


def fetch_jobicy(query: str, count: int = 20) -> List[Dict]:
    response = requests.get(
        JOBICY_URL,
        params={"tag": query, "count": count},
        timeout=20,
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
) -> List[Dict]:
    location_key = (location or "").strip().lower()
    is_remote_mode = remote_only or location_key == "remote"

    # Remote-only mode: skip Adzuna entirely
    if is_remote_mode:
        remotive_jobs: List[Dict] = []
        jobicy_jobs: List[Dict] = []
        try:
            remotive_jobs = fetch_remotive(query=query, limit=20)
        except Exception:
            remotive_jobs = []

        try:
            jobicy_jobs = fetch_jobicy(query=query, count=20)
        except Exception:
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
        except Exception:
            adzuna_city_jobs = []

        if len(adzuna_city_jobs) < 5:
            try:
                adzuna_broad_jobs = fetch_adzuna(query=query, country_code="pk", where="", results_per_page=20)
            except Exception:
                adzuna_broad_jobs = []

        combined_adzuna = dedupe_jobs(adzuna_city_jobs + adzuna_broad_jobs)

        if pakistan_only:
            return dedupe_jobs(_clean_jobs(combined_adzuna))

        if len(combined_adzuna) < 5:
            try:
                remotive_jobs = [j for j in fetch_remotive(query=query, limit=20) if _remote_candidate_filter(j)]
            except Exception:
                remotive_jobs = []
            remote_jobs.extend(_mark_remote(remotive_jobs))

        if len(dedupe_jobs(combined_adzuna + remote_jobs)) < 5:
            try:
                jobicy_jobs = [j for j in fetch_jobicy(query=query, count=20) if _remote_candidate_filter(j)]
            except Exception:
                jobicy_jobs = []
            remote_jobs.extend(_mark_remote(jobicy_jobs))

        return dedupe_jobs(_clean_jobs(combined_adzuna + remote_jobs))

    # Pakistan (no city) or non-city location mode
    adzuna_jobs: List[Dict] = []
    try:
        adzuna_jobs = fetch_adzuna(query=query, country_code=country, where=resolved_where, results_per_page=20)
    except Exception:
        adzuna_jobs = []

    if pakistan_only:
        return dedupe_jobs(_clean_jobs(adzuna_jobs))

    combined = list(adzuna_jobs)

    # standard fallback when both toggles are off
    if len(combined) < 5:
        try:
            remotive_jobs = [j for j in fetch_remotive(query=query, limit=20) if _remote_candidate_filter(j)]
        except Exception:
            remotive_jobs = []
        combined.extend(_mark_remote(remotive_jobs))

    if len(dedupe_jobs(combined)) < 5:
        try:
            jobicy_jobs = [j for j in fetch_jobicy(query=query, count=20) if _remote_candidate_filter(j)]
        except Exception:
            jobicy_jobs = []
        combined.extend(_mark_remote(jobicy_jobs))

    return dedupe_jobs(_clean_jobs(combined))
