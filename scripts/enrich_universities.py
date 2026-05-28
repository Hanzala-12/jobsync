from __future__ import annotations

import argparse
import random
import re
import sys
import time
from collections import defaultdict
from io import StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import quote_plus, urljoin
from xml.etree import ElementTree as ET

import pandas as pd
import requests
from bs4 import BeautifulSoup
from rapidfuzz import fuzz, process
from sqlalchemy import func

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import Base, SessionLocal, engine
from backend.models import Program, Scholarship, University
from backend.services.university_cache import UniversityCache


QS_RANKINGS_URL = "https://raw.githubusercontent.com/shubham9011/QS-World-University-Rankings/master/qs_world_university_rankings_2024.csv"
EWP_CATALOGUE_URL = "https://registry.erasmuswithoutpaper.eu/catalogue-v1.xml"
MALAYSIA_UNIVERSITIES_URL = "https://www.mohe.gov.my/en/institutions/public-universities"
SCHOLARS4DEV_URL = "https://www.scholars4dev.com/"
TOPUNIVERSITIES_URL = "https://www.topuniversities.com/university-rankings"
MASTERSPORTAL_URL = "https://www.mastersportal.com"
THE_RANKINGS_URL = "https://www.timeshighereducation.com/world-university-rankings"
HOTCOURSES_URL = "https://www.hotcoursesabroad.com"

HTTP_CACHE = UniversityCache(ttl_seconds=24 * 60 * 60)
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}

DEFAULT_PROGRAM_TEMPLATES = [
    {"name": "Computer Science", "degree_level": "masters", "duration_years": 2},
    {"name": "Data Science", "degree_level": "masters", "duration_years": 2},
    {"name": "Business Administration", "degree_level": "masters", "duration_years": 2},
]

COUNTRY_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "Malaysia": {"tuition": (8000, 15000), "ielts": 6.0, "toefl": 79, "living": 7000, "intake": "Fall, Spring", "deadline": "2026-01-15"},
    "Singapore": {"tuition": (20000, 35000), "ielts": 6.5, "toefl": 90, "living": 14000, "intake": "Fall", "deadline": "2026-02-28"},
    "Japan": {"tuition": (6000, 18000), "ielts": 6.0, "toefl": 80, "living": 12000, "intake": "Spring, Fall", "deadline": "2026-03-15"},
    "South Korea": {"tuition": (5000, 12000), "ielts": 6.0, "toefl": 79, "living": 11000, "intake": "Spring, Fall", "deadline": "2026-03-01"},
    "China": {"tuition": (4000, 20000), "ielts": 6.0, "toefl": 80, "living": 9000, "intake": "Fall", "deadline": "2026-04-30"},
    "India": {"tuition": (1500, 8000), "ielts": 6.0, "toefl": 75, "living": 5000, "intake": "Fall, Spring", "deadline": "2026-05-31"},
    "Germany": {"tuition": (0, 3500), "ielts": 6.5, "toefl": 88, "living": 12000, "intake": "Fall, Spring", "deadline": "2026-02-28"},
    "Netherlands": {"tuition": (6000, 20000), "ielts": 6.5, "toefl": 90, "living": 13000, "intake": "Fall", "deadline": "2026-02-15"},
    "France": {"tuition": (3000, 15000), "ielts": 6.5, "toefl": 85, "living": 12000, "intake": "Fall", "deadline": "2026-03-01"},
    "Italy": {"tuition": (2000, 12000), "ielts": 6.0, "toefl": 80, "living": 11000, "intake": "Fall", "deadline": "2026-04-15"},
    "Spain": {"tuition": (3000, 16000), "ielts": 6.0, "toefl": 80, "living": 10000, "intake": "Fall", "deadline": "2026-04-30"},
    "United Kingdom": {"tuition": (12000, 32000), "ielts": 6.5, "toefl": 90, "living": 15000, "intake": "Fall", "deadline": "2026-01-31"},
    "United States": {"tuition": (18000, 45000), "ielts": 6.5, "toefl": 90, "living": 15000, "intake": "Fall, Spring", "deadline": "2026-02-15"},
}

EU_COUNTRY_CODES = {
    "AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE", "IT", "LV",
    "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE",
}
EU_COUNTRY_NAMES = {
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Czech Republic", "Denmark", "Estonia",
    "Finland", "France", "Germany", "Greece", "Hungary", "Ireland", "Italy", "Latvia", "Lithuania",
    "Luxembourg", "Malta", "Netherlands", "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain",
    "Sweden",
}
EU_COUNTRY_CODE_TO_NAME = {
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "HR": "Croatia",
    "CY": "Cyprus",
    "CZ": "Czechia",
    "DK": "Denmark",
    "EE": "Estonia",
    "FI": "Finland",
    "FR": "France",
    "DE": "Germany",
    "GR": "Greece",
    "HU": "Hungary",
    "IE": "Ireland",
    "IT": "Italy",
    "LV": "Latvia",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "MT": "Malta",
    "NL": "Netherlands",
    "PL": "Poland",
    "PT": "Portugal",
    "RO": "Romania",
    "SK": "Slovakia",
    "SI": "Slovenia",
    "ES": "Spain",
    "SE": "Sweden",
}
ASIA_COUNTRIES = {"Singapore", "Japan", "South Korea", "China", "India", "Malaysia"}


def _sleep_jitter(min_seconds: float = 2.0, max_seconds: float = 5.0) -> None:
    time.sleep(random.uniform(min_seconds, max_seconds))


def _normalize(value: Optional[str]) -> str:
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", str(value).lower()).strip()


def _extract_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value)
    match = re.search(r"\d+", text)
    if not match:
        return None
    try:
        return int(match.group(0))
    except Exception:
        return None


def _extract_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value)
    match = re.search(r"\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except Exception:
        return None


def _first_non_empty(*values: Any) -> Optional[Any]:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _country_defaults(country: str) -> Dict[str, Any]:
    return COUNTRY_DEFAULTS.get(country, {"tuition": (5000, 18000), "ielts": 6.0, "toefl": 80, "living": 10000, "intake": "Fall", "deadline": "2026-03-31"})


def _parse_rank(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("=", "")
    match = re.search(r"\d+", text)
    if not match:
        return None
    try:
        return int(match.group(0))
    except Exception:
        return None


def _get_university_columns(columns: Sequence[str]) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    name_candidates = ["institution name", "university name", "institution", "university", "name"]
    country_candidates = ["country", "location", "nation"]
    rank_candidates = ["rank", "ranking", "qs world university rankings 2024", "qs rank"]
    website_candidates = ["website", "web page", "web_pages", "url"]

    normalized = {column.lower().strip(): column for column in columns}

    def pick(candidates: Sequence[str]) -> Optional[str]:
        for candidate in candidates:
            if candidate in normalized:
                return normalized[candidate]
        return None

    return pick(name_candidates), pick(country_candidates), pick(rank_candidates), pick(website_candidates)


def _fetch_text(url: str, *, params: Optional[Dict[str, Any]] = None) -> str:
    return HTTP_CACHE.fetch_text(url, params=params, headers=REQUEST_HEADERS, timeout=45)


def _fuzzy_match_university(db, name: str, country: Optional[str] = None) -> Optional[University]:
    if not name:
        return None

    normalized_name = _normalize(name)
    query = db.query(University)
    if country:
        query = query.filter(func.lower(University.country) == country.lower())
    universities = query.all()
    if not universities:
        return None

    for university in universities:
        if _normalize(university.name) == normalized_name:
            return university

    candidates = {university.name: university for university in universities}
    best = process.extractOne(name, list(candidates.keys()), scorer=fuzz.token_set_ratio)
    if best and best[1] >= 92:
        return candidates[best[0]]
    return None


def _upsert_university(db, *, name: str, country: str, city: str = "Unknown", website: Optional[str] = None, ranking_global: Optional[int] = None, ranking_label: Optional[str] = None, logo_url: Optional[str] = None, acceptance_rate: Optional[float] = None, accreditation: Optional[str] = None, student_population: Optional[int] = None) -> University:
    university = _fuzzy_match_university(db, name, country)
    if not university:
        university = University(
            name=name,
            country=country,
            city=city or "Unknown",
            website=website,
            ranking=ranking_label,
            ranking_global=ranking_global,
            logo_url=logo_url,
            acceptance_rate=acceptance_rate,
            accreditation=accreditation,
            student_population=student_population,
        )
        db.add(university)
        db.flush()
        return university

    university.city = university.city or city or "Unknown"
    university.website = website or university.website
    university.ranking = ranking_label or university.ranking
    university.ranking_global = ranking_global or university.ranking_global
    university.logo_url = logo_url or university.logo_url
    university.acceptance_rate = acceptance_rate or university.acceptance_rate
    university.accreditation = accreditation or university.accreditation
    university.student_population = student_population or university.student_population
    return university


def _create_default_programs(db, university: University) -> List[Program]:
    created_programs: List[Program] = []
    existing = db.query(Program).filter(Program.university_id == university.id).count()
    if existing:
        return created_programs

    defaults = _country_defaults(university.country)
    tuition_low, tuition_high = defaults["tuition"]
    for template in DEFAULT_PROGRAM_TEMPLATES:
        estimated_tuition = int((tuition_low + tuition_high) / 2)
        program = Program(
            university_id=university.id,
            name=template["name"],
            degree_level=template["degree_level"],
            duration_years=template["duration_years"],
            estimated_tuition_fees=estimated_tuition,
            currency="USD",
            min_gpa=3.0,
            min_ielts=float(defaults["ielts"]),
            min_toefl=int(defaults["toefl"]),
            application_deadline=defaults["deadline"],
            semester_intake=defaults["intake"],
            living_cost_estimate=int(defaults["living"]),
            scholarship_available=False,
        )
        db.add(program)
        db.flush()
        created_programs.append(program)
    return created_programs


def _discover_program_link(university: University) -> Optional[str]:
    if not university.website:
        return None

    try:
        html = _fetch_text(university.website)
    except Exception:
        return None

    soup = BeautifulSoup(html, "lxml")
    for anchor in soup.find_all("a", href=True):
        label = f"{anchor.get_text(' ', strip=True)} {anchor['href']}".lower()
        if any(keyword in label for keyword in ["program", "course", "study", "admission", "graduate", "postgraduate", "undergraduate"]):
            return urljoin(university.website, anchor["href"])
    return university.website


def _extract_requirements_from_text(text: str) -> Dict[str, Any]:
    if not text:
        return {}
    normalized = text.replace("\u00a0", " ")
    result: Dict[str, Any] = {}

    tuition_match = re.search(r"(?:tuition|fees?|cost).{0,80}?((?:USD|US\$|\$|EUR|€|MYR|SGD|JPY|CNY|INR)\s?\d{1,3}(?:[,\d]{0,6})(?:\.\d+)?)", normalized, re.I)
    if tuition_match:
        result["tuition"] = _extract_int(tuition_match.group(1).replace(",", ""))

    ielts_match = re.search(r"IELTS[^\d]{0,20}(\d+(?:\.\d+)?)", normalized, re.I)
    if ielts_match:
        result["ielts"] = _extract_float(ielts_match.group(1))

    toefl_match = re.search(r"TOEFL[^\d]{0,20}(\d{2,3})", normalized, re.I)
    if toefl_match:
        result["toefl"] = _extract_int(toefl_match.group(1))

    gpa_match = re.search(r"GPA[^\d]{0,20}(\d+(?:\.\d+)?)", normalized, re.I)
    if gpa_match:
        result["gpa"] = _extract_float(gpa_match.group(1))

    deadline_match = re.search(r"(\d{4}-\d{2}-\d{2}|\d{1,2}\s+[A-Za-z]+\s+\d{4})", normalized)
    if deadline_match:
        result["deadline"] = deadline_match.group(1)

    intake = None
    lowered = normalized.lower()
    if "fall" in lowered and "spring" in lowered:
        intake = "Both"
    elif "fall" in lowered or "autumn" in lowered:
        intake = "Fall"
    elif "spring" in lowered:
        intake = "Spring"
    elif "summer" in lowered:
        intake = "Summer"
    if intake:
        result["intake"] = intake
    return result


def _scrape_program_details(university: University) -> Dict[str, Any]:
    detail_pages = [
        f"{MASTERSPORTAL_URL}/search/?q={quote_plus(university.name)}",
        f"{TOPUNIVERSITIES_URL}?search_api_fulltext={quote_plus(university.name)}",
        f"{HOTCOURSES_URL}/search/?query={quote_plus(university.name)}",
    ]

    discovered: Dict[str, Any] = {}
    for url in detail_pages:
        try:
            html = _fetch_text(url)
        except Exception:
            continue

        soup = BeautifulSoup(html, "lxml")
        text = soup.get_text(" ", strip=True)
        extracted = _extract_requirements_from_text(text)
        if extracted:
            discovered.update(extracted)
        if not discovered.get("program_url"):
            for anchor in soup.find_all("a", href=True):
                href = urljoin(url, anchor["href"])
                label = f"{anchor.get_text(' ', strip=True)} {href}".lower()
                if any(keyword in label for keyword in ["program", "course", "degree", "admission", "masters", "bachelors"]):
                    discovered["program_url"] = href
                    break
        if discovered:
            break

    if not discovered:
        discovered = {}

    defaults = _country_defaults(university.country)
    tuition_low, tuition_high = defaults["tuition"]
    discovered.setdefault("tuition", int((tuition_low + tuition_high) / 2))
    discovered.setdefault("ielts", defaults["ielts"])
    discovered.setdefault("toefl", defaults["toefl"])
    discovered.setdefault("gpa", 3.0)
    discovered.setdefault("deadline", defaults["deadline"])
    discovered.setdefault("intake", defaults["intake"])
    discovered.setdefault("living", defaults["living"])
    discovered.setdefault("program_url", _discover_program_link(university) or university.website)
    return discovered


def enrich_qs_rankings(db, *, limit: Optional[int] = 500, country: Optional[str] = None) -> int:
    try:
        csv_text = _fetch_text(QS_RANKINGS_URL)
        dataframe = pd.read_csv(StringIO(csv_text))
    except Exception:
        return 0
    name_column, country_column, rank_column, website_column = _get_university_columns(dataframe.columns)
    if not name_column or not rank_column:
        raise RuntimeError("Unable to detect QS ranking columns")

    records = dataframe.to_dict(orient="records")
    updated = 0
    for index, row in enumerate(records[: limit or 500]):
        row_name = str(row.get(name_column) or row.get(name_column.title()) or "").strip()
        row_country = str(row.get(country_column) or "").strip() if country_column else ""
        if country and row_country.lower() != country.lower():
            continue

        rank_value = _parse_rank(row.get(rank_column))
        if not row_name or rank_value is None:
            continue

        website = str(row.get(website_column) or "").strip() if website_column else ""
        university = _upsert_university(
            db,
            name=row_name,
            country=row_country or country or "Unknown",
            city="Unknown",
            website=website or None,
            ranking_global=rank_value,
            ranking_label=str(row.get(rank_column)).strip(),
        )
        university.ranking_global = rank_value
        if website:
            university.website = website
        updated += 1

        if index % 25 == 0:
            db.flush()

    db.commit()
    return updated


def enrich_programs(db, *, limit: int = 500, country: Optional[str] = None) -> int:
    query = db.query(University)
    if country:
        query = query.filter(func.lower(University.country) == country.lower())
    universities = query.order_by(University.ranking_global.asc().nullslast(), University.name.asc()).limit(limit).all()

    updated_programs = 0
    for university in universities:
        details = _scrape_program_details(university)
        if not university.programs:
            _create_default_programs(db, university)
            db.flush()

        living_cost = details.get("living")
        for program in university.programs:
            if details.get("tuition"):
                program.estimated_tuition_fees = int(details["tuition"])
            defaults = _country_defaults(university.country)
            program.min_gpa = _first_non_empty(program.min_gpa, details.get("gpa"), 3.0)
            program.min_ielts = _first_non_empty(program.min_ielts, details.get("ielts"), defaults["ielts"])
            program.min_toefl = _first_non_empty(program.min_toefl, details.get("toefl"), defaults["toefl"])
            program.application_deadline = _first_non_empty(program.application_deadline, details.get("deadline"), defaults["deadline"])
            program.semester_intake = _first_non_empty(program.semester_intake, details.get("intake"), defaults["intake"])
            program.living_cost_estimate = _first_non_empty(program.living_cost_estimate, living_cost, defaults["living"])
            program.program_url = _first_non_empty(program.program_url, details.get("program_url"), university.website)
            program.scholarship_available = bool(program.scholarship_available or university.scholarships)
            updated_programs += 1

        _sleep_jitter()

    db.commit()
    return updated_programs


def _parse_ewp_records(xml_text: str) -> List[Dict[str, str]]:
    records: List[Dict[str, str]] = []
    try:
        root = ET.fromstring(xml_text)
    except Exception:
        return records

    for element in root.iter():
        attributes = {key.lower(): (value or "").strip() for key, value in element.attrib.items()}
        text = (element.text or "").strip()
        name = _first_non_empty(
            attributes.get("name"),
            attributes.get("hei-name"),
            attributes.get("institution-name"),
            text,
        )
        country = _first_non_empty(
            attributes.get("country"),
            attributes.get("country-code"),
            attributes.get("countrycode"),
            attributes.get("nation"),
        )
        website = _first_non_empty(
            attributes.get("url"),
            attributes.get("website"),
            attributes.get("homepage"),
            attributes.get("href"),
        )
        if not name or not country:
            continue
        records.append({"name": str(name), "country": str(country), "website": str(website or "")})
    return records


def enrich_european_universities(db, *, limit: Optional[int] = None) -> int:
    try:
        xml_text = _fetch_text(EWP_CATALOGUE_URL)
    except Exception:
        return 0

    records = _parse_ewp_records(xml_text)
    updated = 0
    for record in records[: limit or None]:
        country = record["country"]
        country_code = country.upper()
        if country not in EU_COUNTRY_NAMES and country_code not in EU_COUNTRY_CODES:
            continue

        readable_country = EU_COUNTRY_CODE_TO_NAME.get(country_code, country)

        university = _upsert_university(
            db,
            name=record["name"],
            country=readable_country,
            city="Unknown",
            website=record.get("website") or None,
            accreditation="Erasmus+ / EWP",
        )
        university.accreditation = "Erasmus+ / EWP"
        if not university.programs:
            _create_default_programs(db, university)
        updated += 1

        if updated % 25 == 0:
            db.flush()

    db.commit()
    return updated


def _parse_malaysia_university_names(html: str) -> List[str]:
    soup = BeautifulSoup(html, "lxml")
    names: List[str] = []
    for tag in soup.find_all(["a", "h2", "h3", "h4", "li", "td", "strong"]):
        text = tag.get_text(" ", strip=True)
        if not text:
            continue
        normalized = _normalize(text)
        if "universiti" in normalized or "university" in normalized:
            if len(text) >= 4:
                names.append(text)
    return list(dict.fromkeys(names))


def enrich_malaysian_universities(db) -> int:
    try:
        html = _fetch_text(MALAYSIA_UNIVERSITIES_URL)
    except Exception:
        return 0

    names = _parse_malaysia_university_names(html)
    updated = 0
    for index, name in enumerate(names):
        university = _upsert_university(
            db,
            name=name,
            country="Malaysia",
            city="Malaysia",
            accreditation="MOHE Malaysia",
        )
        university.accreditation = "MOHE Malaysia"
        university.logo_url = university.logo_url or None
        if not university.programs:
            _create_default_programs(db, university)

        defaults = _country_defaults("Malaysia")
        tuition_low, tuition_high = defaults["tuition"]
        for program in university.programs:
            program.estimated_tuition_fees = program.estimated_tuition_fees or int((tuition_low + tuition_high) / 2)
            program.min_ielts = program.min_ielts or defaults["ielts"]
            program.min_toefl = program.min_toefl or defaults["toefl"]
            program.application_deadline = program.application_deadline or defaults["deadline"]
            program.semester_intake = program.semester_intake or defaults["intake"]
            program.living_cost_estimate = program.living_cost_estimate or defaults["living"]
            program.program_url = program.program_url or university.website
            program.scholarship_available = program.scholarship_available or True
        updated += 1

        if index % 10 == 0:
            _sleep_jitter(2.0, 3.0)

    db.commit()
    return updated


def enrich_asian_universities(db, *, limit: int = 500) -> int:
    query = db.query(University).filter(University.country.in_(sorted(ASIA_COUNTRIES)))
    universities = query.order_by(University.ranking_global.asc().nullslast(), University.name.asc()).limit(limit).all()
    updated = 0
    for university in universities:
        defaults = _country_defaults(university.country)
        try:
            html = _fetch_text(f"{THE_RANKINGS_URL}?q={quote_plus(university.name)}")
            details = _extract_requirements_from_text(BeautifulSoup(html, "lxml").get_text(" ", strip=True))
        except Exception:
            details = {}

        if not university.programs:
            _create_default_programs(db, university)

        for program in university.programs:
            program.min_ielts = program.min_ielts or details.get("ielts") or defaults["ielts"]
            program.min_toefl = program.min_toefl or details.get("toefl") or defaults["toefl"]
            program.estimated_tuition_fees = program.estimated_tuition_fees or int(sum(defaults["tuition"]) / 2)
            program.application_deadline = program.application_deadline or details.get("deadline") or defaults["deadline"]
            program.semester_intake = program.semester_intake or details.get("intake") or defaults["intake"]
            program.living_cost_estimate = program.living_cost_estimate or defaults["living"]
            program.program_url = program.program_url or university.website
            program.scholarship_available = program.scholarship_available or False
        updated += 1
        _sleep_jitter(2.0, 4.0)

    db.commit()
    return updated


def _extract_deadline(text: str) -> Optional[str]:
    if not text:
        return None
    match = re.search(r"(\d{1,2}\s+[A-Za-z]+\s+\d{4}|\d{4}-\d{2}-\d{2})", text)
    return match.group(1) if match else None


def _extract_amount_usd(text: str) -> Optional[int]:
    if not text:
        return None
    match = re.search(r"(?:USD|US\$|\$)\s?([\d,]{3,})", text, re.I)
    if match:
        return _extract_int(match.group(1).replace(",", ""))
    return None


def enrich_scholarships(db, *, limit: Optional[int] = None) -> int:
    try:
        html = _fetch_text(SCHOLARS4DEV_URL)
    except Exception:
        return 0

    soup = BeautifulSoup(html, "lxml")
    article_links = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(SCHOLARS4DEV_URL, anchor["href"])
        title = anchor.get_text(" ", strip=True)
        if not title or "scholar" not in f"{title} {href}".lower():
            continue
        if href in {item["url"] for item in article_links}:
            continue
        article_links.append({"title": title, "url": href})

    universities = db.query(University).order_by(University.ranking_global.asc().nullslast(), University.name.asc()).all()
    if limit:
        universities = universities[:limit]

    added = 0
    for article in article_links[:50]:
        try:
            article_html = _fetch_text(article["url"])
        except Exception:
            article_html = ""
        article_soup = BeautifulSoup(article_html or html, "lxml")
        article_text = article_soup.get_text(" ", strip=True)
        deadline = _extract_deadline(article_text)
        amount = _extract_amount_usd(article_text)

        for university in universities:
            match_name = _normalize(university.name)
            if match_name not in _normalize(article["title"]) and match_name not in _normalize(article_text):
                continue

            exists_query = (
                db.query(Scholarship)
                .filter(Scholarship.university_id == university.id)
                .filter(func.lower(Scholarship.name) == article["title"].strip().lower())
                .first()
            )
            if exists_query:
                continue

            scholarship = Scholarship(
                name=article["title"].strip(),
                university_id=university.id,
                amount_usd=amount,
                deadline=deadline,
                eligibility_criteria=article_text[:2000],
                application_url=article["url"],
            )
            db.add(scholarship)
            university.accreditation = university.accreditation or university.country
            for program in university.programs:
                program.scholarship_available = True
            added += 1
            break

        if added and added % 10 == 0:
            _sleep_jitter(2.0, 4.0)

    db.commit()
    return added


def run_full_enrichment(*, limit: int = 500, country: Optional[str] = None) -> Dict[str, int]:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        results = {
            "qs_rankings": enrich_qs_rankings(db, limit=limit, country=country),
            "programs": enrich_programs(db, limit=limit, country=country),
            "europe": enrich_european_universities(db),
            "malaysia": enrich_malaysian_universities(db),
            "asia": enrich_asian_universities(db, limit=limit),
            "scholarships": enrich_scholarships(db, limit=limit),
        }
        return results
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Enrich universities with public global data sources")
    parser.add_argument("--full", action="store_true", help="Run all enrichment steps")
    parser.add_argument("--country", type=str, default=None, help="Restrict enrichment to a specific country")
    parser.add_argument("--limit", type=int, default=500, help="Limit the number of universities processed")
    args = parser.parse_args()

    if not args.full:
        raise SystemExit("Use --full to run the enrichment pipeline")

    results = run_full_enrichment(limit=args.limit, country=args.country)
    print("Enrichment complete:")
    for key, value in results.items():
        print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
