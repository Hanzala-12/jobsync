from __future__ import annotations

import logging
import random
import re
import time
from typing import Dict, Iterable, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from sqlalchemy.orm import Session

from config.pakistan_jobs_config import TECH_FILTER_KEYWORDS
from core.deduplicator import process_incoming_job
from core.normalizer import normalize_job

logger = logging.getLogger(__name__)


def random_user_agent() -> str:
    try:
        return UserAgent().random
    except Exception:
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"


def request_html(url: str, timeout: int = 15) -> str:
    response = requests.get(url, timeout=timeout, headers={"User-Agent": random_user_agent()})
    response.raise_for_status()
    return response.text


def soup_for(url: str, timeout: int = 15) -> BeautifulSoup:
    return BeautifulSoup(request_html(url, timeout=timeout), "lxml")


def tech_job(raw_job: Dict) -> bool:
    text = f"{raw_job.get('title', '')} {raw_job.get('description', '')}".lower()
    matches = set()
    for keyword in TECH_FILTER_KEYWORDS:
        normalized = keyword.lower()
        pattern = re.escape(normalized).replace(r"\ ", r"\s+")
        if re.search(rf"\b{pattern}\b", text):
            matches.add(normalized)
            continue
        if any(char in normalized for char in ".+#") and normalized in text:
            matches.add(normalized)

    if not matches:
        return False

    ambiguous_only = {"engineer", "tech", "intern"}
    if matches.issubset(ambiguous_only) and "tech internship" not in text:
        return False
    return True


def normalize_and_store(db: Session, raw_jobs: Iterable[Dict], source: str) -> List[Dict]:
    results = []
    for raw in raw_jobs:
        normalized = normalize_job(raw, source)
        if not normalized.get("title") or not normalized.get("company"):
            continue
        job, action = process_incoming_job(db, normalized)
        results.append({"id": job.id, "title": job.title, "company": job.company, "action": action, "source": source})
    return results


def absolutize(base_url: str, href: str) -> str:
    return urljoin(base_url, href or "")


def sleep_between(min_seconds: float, max_seconds: float) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def detect_captcha(html: str) -> bool:
    lower = html.lower()
    return "captcha" in lower or "verify you are human" in lower or "cloudflare" in lower


def visible_text(element) -> str:
    return " ".join(element.get_text(" ", strip=True).split()) if element else ""
