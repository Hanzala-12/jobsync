"""Backfill job_skills and profile_skills for existing jobs and student profiles.

Run with the project's venv active:

python scripts/backfill_skills.py

This will iterate over jobs and student_profiles and populate the new JSON columns.
"""
from __future__ import annotations

import time
import sys
import os

# ensure repo root is on path
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.database import SessionLocal
from backend.models import Job, StudentProfile
from core.skill_extractor import extract_skills


def backfill_jobs(db):
    jobs = db.query(Job).all()
    print(f"Found {len(jobs)} jobs")
    for j in jobs:
        desc = j.description or ""
        skills = extract_skills(desc, limit=50)
        j.job_skills = skills
    db.commit()


def backfill_profiles(db):
    profiles = db.query(StudentProfile).all()
    print(f"Found {len(profiles)} student profiles")
    for p in profiles:
        text = p.academic_background or ""
        # combine resume_text if available
        if hasattr(p, 'resume_text') and p.resume_text:
            text = (p.resume_text or "") + "\n" + text
        skills = extract_skills(text, limit=50)
        p.profile_skills = skills
    db.commit()


def main():
    db = SessionLocal()
    try:
        backfill_jobs(db)
        backfill_profiles(db)
    finally:
        db.close()


if __name__ == "__main__":
    start = time.time()
    main()
    print("Done in", time.time() - start)
