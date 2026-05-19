from __future__ import annotations

import re
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from typing import Any, Dict, Optional


def normalize_job(raw_job: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Convert raw scraped data into the shared Job shape."""
    apply_url = raw_job.get("apply_url") or raw_job.get("url") or ""
    city = normalize_city(raw_job.get("city") or raw_job.get("location") or "")
    return {
        "title": clean_title(raw_job.get("title", "")),
        "company": clean_company(raw_job.get("company", "")),
        "city": city,
        "location": city or raw_job.get("location") or "",
        "salary": parse_salary(raw_job.get("salary")),
        "job_type": detect_job_type(raw_job.get("job_type", ""), raw_job.get("title", "")),
        "experience_required": raw_job.get("experience") or raw_job.get("experience_required"),
        "posted_date": parse_date(raw_job.get("posted_date")),
        "apply_url": apply_url,
        "url": apply_url,
        "description": clean_description(raw_job.get("description", "")),
        "source": source,
        "scraped_at": datetime.now(),
        "possibly_inactive": bool(raw_job.get("possibly_inactive", False)),
        "external_id": raw_job.get("external_id") or apply_url,
    }


def clean_title(title: str) -> str:
    text = re.sub(r"[^\w\s/+#.-]", " ", str(title or ""))
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return ""
    return " ".join(part.upper() if part.lower() in {"qa", "ai", "it", "ios"} else part.capitalize() for part in text.split())


def clean_company(company: str) -> str:
    text = re.sub(r"[^\w\s&.-]", " ", str(company or ""))
    text = re.sub(r"\s+", " ", text).strip()
    known = {
        "systems ltd": "Systems Limited",
        "systems limited": "Systems Limited",
        "netsol": "NetSol Technologies",
        "netsol technologies": "NetSol Technologies",
        "10pearls": "10Pearls",
        "i2c inc": "i2c Inc",
    }
    return known.get(text.lower().replace(".", ""), text)


def clean_description(description: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(description or ""))
    return re.sub(r"\s+", " ", text).strip()


def normalize_city(city: str) -> str:
    city_map = {
        "lhr": "lahore",
        "lhe": "lahore",
        "labour": "lahore",
        "khi": "karachi",
        "krc": "karachi",
        "isb": "islamabad",
        "isl": "islamabad",
        "rwp": "rawalpindi",
        "rawi": "rawalpindi",
        "pew": "peshawar",
        "psh": "peshawar",
    }
    cleaned = re.sub(r"[^a-zA-Z\s]", " ", str(city or "")).lower().strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if "remote" in cleaned:
        return "remote"
    if "karachi" in cleaned:
        return "karachi"
    if "lahore" in cleaned:
        return "lahore"
    if "islamabad" in cleaned:
        return "islamabad"
    if "rawalpindi" in cleaned:
        return "rawalpindi"
    return city_map.get(cleaned, cleaned)


def detect_job_type(job_type_text: str, title: str) -> str:
    combined = f"{job_type_text} {title}".lower()
    if "intern" in combined:
        return "internship"
    if "remote" in combined:
        return "remote"
    if "contract" in combined:
        return "contract"
    if "part" in combined and "time" in combined:
        return "part-time"
    return "full-time"


def parse_salary(salary_text: Optional[str]) -> str:
    if not salary_text:
        return ""
    text = re.sub(r"\s+", " ", str(salary_text)).strip()
    numbers = re.findall(r"\d[\d,]*", text)
    if len(numbers) >= 2:
        return f"PKR {numbers[0]} - {numbers[1]}"
    return text


def parse_date(date_text: Any) -> Optional[datetime]:
    if isinstance(date_text, datetime):
        return date_text
    if not date_text:
        return None

    text = str(date_text).strip()
    lower = text.lower()
    now = datetime.now()

    match = re.search(r"(\d+)\s+day", lower)
    if match:
        return now - timedelta(days=int(match.group(1)))
    match = re.search(r"(\d+)\s+hour", lower)
    if match:
        return now - timedelta(hours=int(match.group(1)))
    if "today" in lower or "just now" in lower:
        return now
    if "yesterday" in lower:
        return now - timedelta(days=1)

    for fmt in ("%d %b %Y", "%b %d, %Y", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(text.replace("Posted", "").strip(), fmt)
        except ValueError:
            pass

    try:
        parsed = parsedate_to_datetime(text)
        return parsed.replace(tzinfo=None)
    except Exception:
        return None
