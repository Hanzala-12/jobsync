"""Backfill program field provenance after migration.

Usage: python scripts/backfill_field_provenance.py
"""
from datetime import datetime
from backend.database import SessionLocal
from backend.models import Program, University, UniversityVerificationCache, ProgramFieldProvenance

SCRAPABLE_FIELDS = [
    "estimated_tuition_fees",
    "min_gpa",
    "min_ielts",
    "min_toefl",
    "min_gre",
    "application_deadline",
    "semester_intake",
    "scholarship_available",
]


def upsert(db, program_id, field_name, source_type, source_url=None, verified_at=None):
    row = (
        db.query(ProgramFieldProvenance)
        .filter(ProgramFieldProvenance.program_id == program_id, ProgramFieldProvenance.field_name == field_name)
        .first()
    )
    if verified_at is None:
        verified_at = datetime.utcnow()
    if row is None:
        row = ProgramFieldProvenance(program_id=program_id, field_name=field_name, source_type=source_type, source_url=source_url, verified_at=verified_at)
        db.add(row)
    else:
        row.source_type = source_type
        row.source_url = source_url
        row.verified_at = verified_at
    db.commit()
    db.refresh(row)
    return row


def main():
    db = SessionLocal()
    try:
        programs = db.query(Program).all()
        for program in programs:
            uni = db.query(University).filter(University.id == program.university_id).first()
            source = program.source_url or program.program_url or (uni.website if uni else None)
            if int(program.data_quality_score or 1) >= 3:
                # mark all scrapable fields as official
                for f in SCRAPABLE_FIELDS:
                    upsert(db, program.id, f, "official", source)
            elif int(program.data_quality_score or 1) == 2:
                # mark tuition as estimated if verification cache has it
                cache = (
                    db.query(UniversityVerificationCache)
                    .filter(UniversityVerificationCache.program_id == program.id, UniversityVerificationCache.university_id == program.university_id)
                    .first()
                )
                for f in SCRAPABLE_FIELDS:
                    if f == "estimated_tuition_fees":
                        if cache and cache.tuition_estimated is not None:
                            upsert(db, program.id, f, "estimated", cache.source_url)
                        else:
                            upsert(db, program.id, f, "default", None)
                    else:
                        # unknown fields — leave as default unless cache indicates something
                        upsert(db, program.id, f, "default", None)
            else:
                # default: ensure defaults exist
                for f in SCRAPABLE_FIELDS:
                    upsert(db, program.id, f, "default", None)
        print(f"Backfilled provenance for {len(programs)} programs")
    finally:
        db.close()


if __name__ == "__main__":
    main()
