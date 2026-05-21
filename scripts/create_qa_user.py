from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.database import SessionLocal
from backend.models import User
from datetime import datetime

def main():
    db = SessionLocal()
    try:
        email = 'qa@example.com'
        user = db.query(User).filter(User.email == email).first()
        if user:
            print('User exists:', user.email)
            return 0
        user = User(email=email, hashed_password='testing', is_active=True, created_at=datetime.utcnow())
        db.add(user)
        db.commit()
        print('Created user:', email)
        return 0
    finally:
        db.close()

if __name__ == '__main__':
    raise SystemExit(main())
