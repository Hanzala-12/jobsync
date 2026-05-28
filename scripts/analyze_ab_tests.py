from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict

from sqlalchemy import and_, func

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.models import ABTest, ABTestAssignment, ABTestEvent


def _window_start(days: int) -> datetime:
    return datetime.utcnow() - timedelta(days=max(1, int(days)))


def _rates(db, test_id: int, variant: str, since: datetime) -> Dict[str, float]:
    assignments_count = (
        db.query(func.count(ABTestAssignment.id))
        .filter(ABTestAssignment.ab_test_id == test_id, ABTestAssignment.variant == variant)
        .scalar()
        or 0
    )
    if assignments_count <= 0:
        return {
            "users": 0,
            "save_users": 0,
            "apply_users": 0,
            "save_rate": 0.0,
            "apply_rate": 0.0,
        }

    save_users = (
        db.query(func.count(func.distinct(ABTestEvent.user_id)))
        .filter(
            ABTestEvent.ab_test_id == test_id,
            ABTestEvent.event_type == "save",
            ABTestEvent.timestamp >= since,
            ABTestEvent.assignment_id.in_(
                db.query(ABTestAssignment.id).filter(
                    ABTestAssignment.ab_test_id == test_id,
                    ABTestAssignment.variant == variant,
                )
            ),
        )
        .scalar()
        or 0
    )

    apply_users = (
        db.query(func.count(func.distinct(ABTestEvent.user_id)))
        .filter(
            ABTestEvent.ab_test_id == test_id,
            ABTestEvent.event_type == "apply",
            ABTestEvent.timestamp >= since,
            ABTestEvent.assignment_id.in_(
                db.query(ABTestAssignment.id).filter(
                    ABTestAssignment.ab_test_id == test_id,
                    ABTestAssignment.variant == variant,
                )
            ),
        )
        .scalar()
        or 0
    )

    return {
        "users": int(assignments_count),
        "save_users": int(save_users),
        "apply_users": int(apply_users),
        "save_rate": round(float(save_users) / float(assignments_count), 4),
        "apply_rate": round(float(apply_users) / float(assignments_count), 4),
    }


def generate_report(days: int = 30) -> Dict[str, object]:
    since = _window_start(days)
    db = SessionLocal()
    try:
        tests = db.query(ABTest).filter(ABTest.is_active.is_(True)).order_by(ABTest.feature_key.asc()).all()
        report = {
            "generated_at": datetime.utcnow().isoformat(),
            "window_days": int(days),
            "tests": [],
        }
        for test in tests:
            control = _rates(db, int(test.id), "control", since)
            treatment = _rates(db, int(test.id), "treatment", since)
            report["tests"].append(
                {
                    "feature_key": test.feature_key,
                    "name": test.name,
                    "control": control,
                    "treatment": treatment,
                    "deltas": {
                        "save_rate": round(treatment["save_rate"] - control["save_rate"], 4),
                        "apply_rate": round(treatment["apply_rate"] - control["apply_rate"], 4),
                    },
                }
            )
        return report
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze A/B test conversions for save/apply actions")
    parser.add_argument("--days", type=int, default=30, help="Number of trailing days to include")
    parser.add_argument("--out", type=str, default="", help="Optional file path to save JSON report")
    args = parser.parse_args()

    report = generate_report(days=args.days)
    payload = json.dumps(report, indent=2)
    print(payload)
    if args.out:
        output_path = Path(args.out)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")


if __name__ == "__main__":
    main()
