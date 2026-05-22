"""Count rows in the jobs table and print the result."""
import sys, os
sys.path.insert(0, os.path.abspath('.'))
from backend.database import SessionLocal
from sqlalchemy import text

def main():
    db = SessionLocal()
    try:
        r = db.execute(text('SELECT COUNT(*) FROM jobs')).scalar()
        print('jobs_count:', r)
    finally:
        db.close()

if __name__ == '__main__':
    main()
