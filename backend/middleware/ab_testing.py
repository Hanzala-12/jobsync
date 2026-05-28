from __future__ import annotations

from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware

from backend.database import SessionLocal
from backend.security import decode_token
from backend.services.ab_testing_service import assign_user_for_all_features, is_enabled


class ABTestingAssignmentMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request.state.ab_assignments = {}

        if not is_enabled():
            return await call_next(request)

        if not request.url.path.startswith(("/api/student", "/student")):
            return await call_next(request)

        user_id = _user_id_from_auth_header(request.headers.get("authorization"))
        if not user_id:
            return await call_next(request)

        db = SessionLocal()
        try:
            assignments = assign_user_for_all_features(db, user_id)
            request.state.ab_assignments = {
                key: {
                    "variant": value.variant,
                    "algorithm_version": value.algorithm_version,
                }
                for key, value in assignments.items()
            }
        except Exception:
            # Best-effort middleware: do not block request flow on A/B errors.
            request.state.ab_assignments = {}
        finally:
            db.close()

        return await call_next(request)


def _user_id_from_auth_header(auth_header: Optional[str]) -> Optional[int]:
    if not auth_header:
        return None
    parts = auth_header.strip().split(" ", 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        return None
    token = parts[1].strip()
    if not token:
        return None
    try:
        payload = decode_token(token)
        subject = payload.get("sub")
        return int(str(subject)) if subject is not None else None
    except Exception:
        return None
