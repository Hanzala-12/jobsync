from __future__ import annotations

import base64
import hashlib
import os
from typing import Iterable

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from backend.models import UserApiKey

DEFAULT_PROVIDERS = ("openrouter", "groq", "openai")


def normalize_provider(provider: str) -> str:
    return str(provider or "").strip().lower()


def _fernet() -> Fernet:
    explicit = (os.getenv("API_KEY_ENCRYPTION_KEY") or "").strip()
    if explicit:
        key = explicit.encode("utf-8")
    else:
        seed = (os.getenv("SECRET_KEY") or "jobsync-dev-secret-change-me").encode("utf-8")
        key = base64.urlsafe_b64encode(hashlib.sha256(seed).digest())
    return Fernet(key)


def encrypt_api_key(api_key: str) -> str:
    return _fernet().encrypt(str(api_key or "").encode("utf-8")).decode("utf-8")


def decrypt_api_key(encrypted_api_key: str) -> str:
    try:
        return _fernet().decrypt(str(encrypted_api_key or "").encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return ""


def list_user_api_key_statuses(db: Session, user_id: int, providers: Iterable[str] = DEFAULT_PROVIDERS) -> list[dict[str, object]]:
    rows = db.query(UserApiKey.provider).filter(UserApiKey.user_id == user_id).all()
    existing = {normalize_provider(row[0]) for row in rows}
    return [{"provider": normalize_provider(provider), "has_key": normalize_provider(provider) in existing} for provider in providers]


def get_user_api_key_value(db: Session, user_id: int, provider: str) -> str:
    row = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user_id, UserApiKey.provider == normalize_provider(provider))
        .first()
    )
    if not row:
        return ""
    return decrypt_api_key(row.encrypted_api_key)


def upsert_user_api_key(db: Session, user_id: int, provider: str, api_key: str) -> UserApiKey:
    provider_name = normalize_provider(provider)
    row = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user_id, UserApiKey.provider == provider_name)
        .first()
    )
    encrypted = encrypt_api_key(api_key)
    if row is None:
        row = UserApiKey(user_id=user_id, provider=provider_name, encrypted_api_key=encrypted)
        db.add(row)
    else:
        row.encrypted_api_key = encrypted
    db.commit()
    db.refresh(row)
    return row


def delete_user_api_key(db: Session, user_id: int, provider: str) -> bool:
    provider_name = normalize_provider(provider)
    row = (
        db.query(UserApiKey)
        .filter(UserApiKey.user_id == user_id, UserApiKey.provider == provider_name)
        .first()
    )
    if not row:
        return False
    db.delete(row)
    db.commit()
    return True