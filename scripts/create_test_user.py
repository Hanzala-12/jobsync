from backend.database import SessionLocal
from backend.models import User
from backend.security import hash_password

email = "autotest+e2e2026@example.com"
name = "E2E Tester"
password = "TestPass123!"

session = SessionLocal()
try:
    existing = session.query(User).filter(User.email == email).first()
    if existing:
        print("already_exists")
    else:
        user = User(email=email, hashed_password=hash_password(password), name=name, is_active=True, token_version=0)
        session.add(user)
        session.commit()
        print(f"created:{user.id}")
finally:
    session.close()
