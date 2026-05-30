from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import UserApiKeyDeleteResponse, UserApiKeyStatus, UserApiKeyUpsertRequest
from backend.security import get_current_user
from backend.services.user_api_keys import DEFAULT_PROVIDERS, delete_user_api_key, list_user_api_key_statuses, normalize_provider, upsert_user_api_key

router = APIRouter(prefix="/settings", tags=["Settings"])


@router.get("/keys", response_model=list[UserApiKeyStatus])
def list_keys(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [UserApiKeyStatus(**item) for item in list_user_api_key_statuses(db, current_user.id, DEFAULT_PROVIDERS)]


@router.post("/keys", response_model=UserApiKeyStatus)
def save_key(payload: UserApiKeyUpsertRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    provider = normalize_provider(payload.provider)
    if provider not in DEFAULT_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    upsert_user_api_key(db, current_user.id, provider, payload.api_key)
    return UserApiKeyStatus(provider=provider, has_key=True)


@router.delete("/keys/{provider}", response_model=UserApiKeyDeleteResponse)
def delete_key(provider: str, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    provider_name = normalize_provider(provider)
    if provider_name not in DEFAULT_PROVIDERS:
        raise HTTPException(status_code=400, detail="Unsupported provider")
    delete_user_api_key(db, current_user.id, provider_name)
    return UserApiKeyDeleteResponse(success=True)