from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.database import SessionLocal
from backend.models import StudentProfile
from backend.services.university_match_service import retrieve_similar_programs, get_match_for_program


def main():
    db = SessionLocal()
    try:
        profile = db.query(StudentProfile).order_by(StudentProfile.id.desc()).first()
        if not profile:
            print('No student profiles found')
            return
        print('Using student profile id:', profile.id)
        candidates = retrieve_similar_programs(profile.id, limit=5, db=db)
        print('Candidates count:', len(candidates))
        for i, c in enumerate(candidates[:5], 1):
            print(f'Candidate {i}: program_id={c.get("program_id")}, vector_similarity={c.get("vector_similarity")}')
            match = get_match_for_program(profile.id, int(c.get('program_id')), db)
            print('Match keys:', list(match.keys()))
            print('Match id:', match.get('id'))
            print('---')
    finally:
        db.close()


if __name__ == '__main__':
    main()
