import os
from fastapi import Request
from fastapi.responses import RedirectResponse
from starlette.middleware.base import BaseHTTPMiddleware


class HTTPSRedirectMiddleware(BaseHTTPMiddleware):
    """Redirect all HTTP requests to HTTPS in production."""

    def __init__(self, app, enabled: bool = True):
        super().__init__(app)
        self.enabled = enabled

    async def dispatch(self, request, call_next):
        if (
            self.enabled
            and request.headers.get("x-forwarded-proto", "") == "http"
        ):
            url = request.url.replace(scheme="https")
            return RedirectResponse(str(url))
        return await call_next(request)
