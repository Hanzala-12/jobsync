from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import User
from backend.schemas import AuthToken, UserCreate, UserLogin, UserOut
from backend.security import (
    create_access_token,
    create_refresh_token,
    create_access_token_for_user,
    create_refresh_token_for_user,
    get_current_user,
    get_user_by_id,
    get_user_by_email,
    hash_password,
    verify_password,
    decode_token,
)


router = APIRouter(prefix="/auth", tags=["Auth"])


def _token_response(user: User) -> AuthToken:
    return AuthToken(
        access_token=create_access_token_for_user(user),
        refresh_token=create_refresh_token_for_user(user),
        user=UserOut.model_validate(user),
    )


@router.post("/signup", response_model=AuthToken)
def signup(payload: UserCreate, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if not email:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Email is required")
    if len(payload.password) < 8:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Password must be at least 8 characters")

    existing = get_user_by_email(db, email)
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An account with this email already exists")

    user = User(email=email, hashed_password=hash_password(payload.password), name=payload.name, is_active=True, token_version=0)
    db.add(user)
    db.commit()
    db.refresh(user)
    return _token_response(user)


@router.post("/login", response_model=AuthToken)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = get_user_by_email(db, email)
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")
    return _token_response(user)


@router.post("/refresh", response_model=AuthToken)
def refresh(payload: dict, db: Session = Depends(get_db)):
    refresh_token = str(payload.get("refresh_token") or "").strip()
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="refresh_token is required")

    decoded = decode_token(refresh_token)
    if decoded.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

    try:
        user_id = int(str(decoded.get("sub") or "").strip())
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    if int(decoded.get("ver", 0) or 0) != int(getattr(user, "token_version", 0) or 0):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has been revoked")
    return _token_response(user)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.token_version = int(getattr(current_user, "token_version", 0) or 0) + 1
    db.commit()
    return {"success": True}