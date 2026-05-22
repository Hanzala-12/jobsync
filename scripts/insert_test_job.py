"""Insert a single test job row via SQLAlchemy for local testing."""
import sys, os
sys.path.insert(0, os.path.abspath('.'))
from backend.database import SessionLocal
from backend.models import Job
from datetime import datetime

def main():
    db = SessionLocal()
    try:
        job = Job(
            source='test',
            external_id='test-1',
            title='Test Software Engineer',
            company='Acme Corp',
            location='Remote',
            city='Remote',
            description='We are looking for a software engineer with Python, FastAPI, SQLAlchemy experience.',
            url='https://example.com/job/test-1',
            apply_url='https://example.com/apply/test-1',
            posted_date=str(datetime.utcnow()),
            salary='Competitive',
            job_type='Full-time',
            experience_required='2+ years',
        )
        db.add(job)
        db.commit()
        print('Inserted job id', job.id)
    except Exception as e:
        print('Insert failed', e)
    finally:
        db.close()

if __name__ == '__main__':
    main()
