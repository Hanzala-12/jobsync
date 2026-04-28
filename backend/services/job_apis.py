import requests
from typing import List
import os
from backend.models import Job
from datetime import datetime

REMOTEOK_URL = "https://remoteok.com/api"
ARBEITNOW_URL = "https://arbeitnow.com/api/job-board-api"
ADZUNA_URL = "https://api.adzuna.com/v1/api/jobs/gb/search/1"   # example: GB

def fetch_remoteok(query: str = "developer") -> List[dict]:
    try:
        resp = requests.get(REMOTEOK_URL, params={"tag": query}, timeout=10)
        data = resp.json()
        jobs = []
        for idx, item in enumerate(data):
            if idx == 0:  # first element is legal notice
                continue
            jobs.append({
                "source": "remoteok",
                "external_id": f"remoteok-{item.get('id')}",
                "title": item.get("position"),
                "company": item.get("company"),
                "location": item.get("location", "Remote"),
                "description": item.get("description", ""),
                "url": item.get("url") or f"https://remoteok.com/remote-jobs/{item.get('id')}",
                "posted_date": item.get("date", "")
            })
        return jobs
    except Exception:
        return []

def fetch_arbeitnow() -> List[dict]:
    try:
        resp = requests.get(ARBEITNOW_URL, timeout=10)
        data = resp.json().get("data", [])
        jobs = []
        for item in data:
            jobs.append({
                "source": "arbeitnow",
                "external_id": f"arbeitnow-{item['slug']}",
                "title": item["title"],
                "company": item["company_name"],
                "location": item["location"],
                "description": item.get("description", ""),
                "url": item["url"],
                "posted_date": item.get("created_at", "")
            })
        return jobs
    except Exception:
        return []

def fetch_adzuna(query: str = "software engineer") -> List[dict]:
    app_id = os.getenv("ADZUNA_APP_ID")
    app_key = os.getenv("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        return []
    try:
        resp = requests.get(ADZUNA_URL, params={
            "app_id": app_id,
            "app_key": app_key,
            "what": query,
            "content-type": "application/json"
        }, timeout=10)
        data = resp.json().get("results", [])
        jobs = []
        for item in data:
            jobs.append({
                "source": "adzuna",
                "external_id": f"adzuna-{item['id']}",
                "title": item["title"],
                "company": item.get("company", {}).get("display_name", "Unknown"),
                "location": item.get("location", {}).get("display_name", ""),
                "description": item.get("description", ""),
                "url": item.get("redirect_url"),
                "posted_date": item.get("created", "")
            })
        return jobs
    except Exception:
        return []

def fetch_all_jobs(query: str = "developer") -> List[dict]:
    all_jobs = []
    all_jobs.extend(fetch_remoteok(query))
    all_jobs.extend(fetch_arbeitnow())
    all_jobs.extend(fetch_adzuna(query))
    # de-duplicate by external_id
    seen = set()
    unique = []
    for job in all_jobs:
        if job["external_id"] not in seen:
            seen.add(job["external_id"])
            unique.append(job)
    return unique
