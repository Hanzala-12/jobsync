from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Dict, Iterable, Optional, Tuple

import requests
from sqlalchemy import func

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.models import University


logger = logging.getLogger("enrich_us_universities")

COLLEGE_SCORECARD_API_URL = os.getenv(
    "COLLEGE_SCORECARD_API_URL",
    "https://api.data.gov/ed/collegescorecard/v1/schools",
).strip()
COLLEGE_SCORECARD_API_KEY = os.getenv("COLLEGE_SCORECARD_API_KEY", "").strip()
ENABLE_US_UNIVERSITY_ENRICHMENT = os.getenv("ENABLE_US_UNIVERSITY_ENRICHMENT", "false").strip().lower() == "true"

SCORECARD_FIELDS = [
    "school.name",
    "school.city",
    "school.state",
    "school.ownership",
    "latest.admissions.admission_rate.overall",
    "latest.admissions.sat_scores.average.overall",
    "latest.admissions.act_scores.midpoint.cumulative",
    "latest.cost.avg_net_price.overall",
]


def _normalize(value: Any) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _to_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(round(float(value)))
    except Exception:
        return None


def _to_float(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except Exception:
        return None


def _is_public_school(ownership: Any) -> bool:
    ownership_text = _normalize(ownership)
    return ownership_text == "1" or "public" in ownership_text


def _school_name_similarity(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    left_norm = _normalize(left)
    right_norm = _normalize(right)
    if left_norm == right_norm:
        return 1.0
    return SequenceMatcher(None, left_norm, right_norm).ratio()


def _pick_best_match(university: University, results: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    best_result: Optional[Dict[str, Any]] = None
    best_score = 0.0
    university_city = _normalize(university.city)

    for result in results:
        school_name = str(result.get("school.name") or "")
        school_city = _normalize(result.get("school.city"))
        similarity = _school_name_similarity(university.name or "", school_name)
        if university_city and school_city and university_city == school_city:
            similarity += 0.1
        if similarity > best_score:
            best_score = similarity
            best_result = result

    if best_score < 0.65:
        return None
    return best_result


def _scorecard_request(session: requests.Session, university: University, *, timeout: int, delay_seconds: float, retries: int) -> Optional[Dict[str, Any]]:
    if not COLLEGE_SCORECARD_API_KEY:
        raise RuntimeError("COLLEGE_SCORECARD_API_KEY is required")

    params = {
        "api_key": COLLEGE_SCORECARD_API_KEY,
        "per_page": 20,
        "fields": ",".join(SCORECARD_FIELDS),
        "school.name": university.name,
    }
    if university.city:
        params["school.city"] = university.city

    last_error: Optional[Exception] = None
    for attempt in range(1, max(1, retries) + 1):
        try:
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            response = session.get(COLLEGE_SCORECARD_API_URL, params=params, timeout=timeout)
            if response.status_code in {429, 500, 502, 503, 504}:
                raise RuntimeError(f"Scorecard API returned {response.status_code}")
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise RuntimeError("Unexpected College Scorecard API response")
            return payload
        except Exception as exc:
            last_error = exc
            logger.warning(
                "College Scorecard request failed for university_id=%s attempt=%s/%s: %s",
                university.id,
                attempt,
                retries,
                exc,
            )
            if attempt < retries:
                time.sleep(min(30.0, max(1.0, delay_seconds) * attempt))

    if last_error:
        raise last_error
    return None


def _apply_scorecard_data(university: University, match: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    updated = False
    changes: Dict[str, Any] = {}

    acceptance_rate = _to_float(match.get("latest.admissions.admission_rate.overall"))
    avg_sat = _to_int(match.get("latest.admissions.sat_scores.average.overall"))
    avg_act = _to_float(match.get("latest.admissions.act_scores.midpoint.cumulative"))
    net_price = _to_int(match.get("latest.cost.avg_net_price.overall"))
    ownership = match.get("school.ownership")

    if acceptance_rate is not None and university.acceptance_rate != acceptance_rate:
        university.acceptance_rate = acceptance_rate
        changes["acceptance_rate"] = acceptance_rate
        updated = True
    if avg_sat is not None and university.avg_sat != avg_sat:
        university.avg_sat = avg_sat
        changes["avg_sat"] = avg_sat
        updated = True
    if avg_act is not None and university.avg_act != avg_act:
        university.avg_act = avg_act
        changes["avg_act"] = avg_act
        updated = True
    if net_price is not None:
        if _is_public_school(ownership):
            if university.net_price_public != net_price:
                university.net_price_public = net_price
                changes["net_price_public"] = net_price
                updated = True
        else:
            if university.net_price_private != net_price:
                university.net_price_private = net_price
                changes["net_price_private"] = net_price
                updated = True

    if updated:
        university.last_scraped_at = datetime.utcnow()
        changes["last_scraped_at"] = university.last_scraped_at.isoformat()

    return updated, changes


def enrich_us_universities(*, limit: Optional[int], delay_seconds: float, timeout: int, retries: int, dry_run: bool = False) -> Dict[str, int]:
    if not ENABLE_US_UNIVERSITY_ENRICHMENT:
        raise RuntimeError("ENABLE_US_UNIVERSITY_ENRICHMENT must be true to run this script")

    session = requests.Session()
    session.headers.update({"User-Agent": "JobSyncPro/CollegeScorecardEnricher"})

    db = SessionLocal()
    stats = {"processed": 0, "updated": 0, "skipped": 0, "matched": 0, "errors": 0}
    try:
        universities = (
            db.query(University)
            .filter(func.lower(University.country).in_(["united states", "united states of america", "usa", "us"]))
            .order_by(University.name.asc(), University.id.asc())
            .all()
        )
        if limit is not None:
            universities = universities[: max(0, limit)]

        for university in universities:
            stats["processed"] += 1
            try:
                payload = _scorecard_request(session, university, timeout=timeout, delay_seconds=delay_seconds, retries=retries)
                if not payload:
                    stats["skipped"] += 1
                    continue

                results = payload.get("results") or []
                if not isinstance(results, list) or not results:
                    stats["skipped"] += 1
                    continue

                best_match = _pick_best_match(university, results)
                if not best_match:
                    logger.info("No reliable Scorecard match for university_id=%s name=%s", university.id, university.name)
                    stats["skipped"] += 1
                    continue

                stats["matched"] += 1
                updated, changes = _apply_scorecard_data(university, best_match)
                if updated:
                    stats["updated"] += 1
                    logger.info("Updated university_id=%s changes=%s", university.id, changes)
                    if not dry_run:
                        db.commit()
                else:
                    stats["skipped"] += 1
                    if not dry_run:
                        db.rollback()
            except Exception as exc:
                stats["errors"] += 1
                db.rollback()
                logger.exception("Failed to enrich university_id=%s name=%s: %s", university.id, university.name, exc)

        return stats
    finally:
        db.close()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Enrich US universities with College Scorecard data")
    parser.add_argument("--limit", type=int, default=None, help="Maximum number of US universities to process")
    parser.add_argument("--delay-seconds", type=float, default=1.0, help="Delay between API requests to respect rate limits")
    parser.add_argument("--timeout", type=int, default=30, help="HTTP timeout for Scorecard requests")
    parser.add_argument("--retries", type=int, default=3, help="Number of retries per university")
    parser.add_argument("--dry-run", action="store_true", help="Fetch and match data without committing updates")
    return parser


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    args = _build_parser().parse_args()
    stats = enrich_us_universities(
        limit=args.limit,
        delay_seconds=max(0.0, float(args.delay_seconds)),
        timeout=max(1, int(args.timeout)),
        retries=max(1, int(args.retries)),
        dry_run=bool(args.dry_run),
    )
    logger.info("Enrichment finished: %s", stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())