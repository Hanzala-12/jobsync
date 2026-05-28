from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.models import Program, StudentProfile, University
from backend.services.university_verification_service import verify_program_live


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify live tuition and admissions data for a university program")
    parser.add_argument("--university-id", type=int, required=True)
    parser.add_argument("--program-id", type=int, required=True)
    parser.add_argument("--student-profile-id", type=int, default=None)
    parser.add_argument("--refresh", action="store_true", help="Force a live refresh instead of using the cache")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON response")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        university = db.query(University).filter(University.id == args.university_id).first()
        program = db.query(Program).filter(Program.id == args.program_id, Program.university_id == args.university_id).first()
        if not university or not program:
            raise SystemExit("University or program not found")

        student_profile = None
        if args.student_profile_id is not None:
            student_profile = db.query(StudentProfile).filter(StudentProfile.id == args.student_profile_id).first()

        result = verify_program_live(db, university, program, student_profile=student_profile, refresh=args.refresh)
        print(json.dumps(result, indent=2 if args.pretty else None, ensure_ascii=False, default=str))
    finally:
        db.close()


if __name__ == "__main__":
    main()
