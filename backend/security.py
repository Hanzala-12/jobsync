from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta, timezone
from contextvars import ContextVar
from typing import Any, Dict

from fastapi import Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from passlib.exc import UnknownHashError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User


DEFAULT_SECRET_KEY = "jobsync-dev-secret-change-me"
_ENV_SECRET_KEY = os.getenv("SECRET_KEY", "").strip()
if _ENV_SECRET_KEY:
    SECRET_KEY = _ENV_SECRET_KEY
else:
    runtime_env = os.getenv("ENV", "").strip().lower()
    if runtime_env == "development":
        SECRET_KEY = secrets.token_urlsafe(48)
    else:
        raise RuntimeError("SECRET_KEY must be set in production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = max(1, int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440")))
REFRESH_TOKEN_EXPIRE_DAYS = max(1, int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "14")))

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)
current_user_id_context: ContextVar[int | None] = ContextVar("current_user_id_context", default=None)


if not _ENV_SECRET_KEY:
    import warnings

    warnings.warn(
        "SECRET_KEY is not set; using a per-process development secret. Set SECRET_KEY in production and ENV=development locally.",
        UserWarning,
    )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Normalize incoming password to match hashing behavior.
    try:
        normalized = _normalize_password(plain_password)
    except Exception:
        normalized = plain_password

    try:
        return pwd_context.verify(normalized, hashed_password)
    except UnknownHashError:
        # Stored hash might use bcrypt. Try a bcrypt-only context as a fallback.
        try:
            alt = CryptContext(schemes=["bcrypt"], deprecated="auto")
            return alt.verify(normalized, hashed_password)
        except Exception:
            return False


def hash_password(password: str) -> str:
    # bcrypt truncates inputs longer than 72 bytes which raises errors in some
    # passlib backends. Truncate to 72 bytes deterministically before hashing.
    normalized = _normalize_password(password)
    return pwd_context.hash(normalized)


def _normalize_password(password: str) -> str:
    if password is None:
        return ''
    if not isinstance(password, str):
        password = str(password)
    # Encode to UTF-8, truncate to 72 bytes, then decode ignoring partial
    # sequences so we get a stable string form that maps to the same bytes.
    b = password.encode('utf-8')
    if len(b) <= 72:
        return password
    truncated = b[:72]
    return truncated.decode('utf-8', errors='ignore')


def create_token(subject: str, expires_delta: timedelta, token_type: str) -> str:
    payload: Dict[str, Any] = {
        "sub": subject,
        "type": token_type,
        "exp": datetime.now(timezone.utc) + expires_delta,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_access_token(subject: str) -> str:
    return create_token(subject, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES), "access")


def create_refresh_token(subject: str) -> str:
    return create_token(subject, timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS), "refresh")


def decode_token(token: str) -> Dict[str, Any]:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.query(User).filter(User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def _token_version_for_user(user: User) -> int:
    return int(getattr(user, "token_version", 0) or 0)


def create_access_token_for_user(user: User) -> str:
    payload: Dict[str, Any] = {
        "sub": str(user.id),
        "type": "access",
        "ver": _token_version_for_user(user),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
    }
    current_user_id_context.set(int(user.id))
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token_for_user(user: User) -> str:
    payload: Dict[str, Any] = {
        "sub": str(user.id),
        "type": "refresh",
        "ver": _token_version_for_user(user),
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def set_current_user_context(user_id: int | None) -> None:
    current_user_id_context.set(int(user_id) if user_id is not None else None)


def get_current_user_context() -> int | None:
    return current_user_id_context.get()


def get_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    # TESTING_MODE bypass removed for security. Use proper test fixtures instead.
    # This prevents accidental auth bypass in production.
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    try:
        user_id = int(str(subject))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if int(payload.get("ver", 0) or 0) != _token_version_for_user(user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    set_current_user_context(user.id)
    return user


def get_optional_current_user(token: str | None = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User | None:
    if not token:
        return None
    try:
        user = get_current_user(token=token, db=db)
        if user:
            set_current_user_context(user.id)
        return user
    except HTTPException:
        return None


def get_current_user_from_stream(
    token: str | None = Depends(oauth2_scheme),
    stream_token: str | None = Query(default=None, alias="token"),
    db: Session = Depends(get_db),
) -> User:
    resolved_token = token or stream_token
    if not resolved_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_token(resolved_token)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    subject = payload.get("sub")
    if not subject:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    try:
        user_id = int(str(subject))
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if int(payload.get("ver", 0) or 0) != _token_version_for_user(user):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    set_current_user_context(user.id)
    return user


def require_current_user(user: User = Depends(get_current_user)) -> User:
    return user