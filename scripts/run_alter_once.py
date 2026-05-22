import sys
import os
from sqlalchemy import text

# ensure repo root
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from backend.database import engine
print('engine url:', getattr(engine, 'url', None))

def main():
    conn = engine.connect()
    print('dialect:', engine.dialect.name)
    try:
        conn.execute(text("ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS profile_skills JSON DEFAULT '[]'::jsonb"))
        print('added profile_skills')
    except Exception as e:
        print('profile_skills add failed', e)
    try:
        conn.execute(text("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_skills JSON DEFAULT '[]'::jsonb"))
        print('added job_skills')
    except Exception as e:
        print('job_skills add failed', e)
    conn.close()

if __name__ == '__main__':
    main()
