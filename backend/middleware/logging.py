import logging
import sys
import time
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
try:
    from pythonjsonlogger import jsonlogger
    _HAS_JSONLOGGER = True
except Exception:  # pragma: no cover - optional dependency in lightweight dev envs
    jsonlogger = None
    _HAS_JSONLOGGER = False

from backend.monitoring import record_http_request


_STANDARD_LOG_RECORD_ATTRS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value)
        return value
    except Exception:
        return str(value)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        if _HAS_JSONLOGGER and jsonlogger is not None:
            formatter = jsonlogger.JsonFormatter(
                "timestamp level module message request_id method path status duration_ms",
                rename_fields={"levelname": "level", "name": "module", "message": "message"},
            )
        else:
            # Fallback plain formatter when pythonjsonlogger isn't available
            formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
        record.timestamp = datetime.now(timezone.utc).isoformat()
        if not getattr(record, "request_id", None):
            record.request_id = None
        if record.exc_info:
            record.exception = self.formatException(record.exc_info)
        return formatter.format(record)


def configure_logging(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(level)
    root_logger.addHandler(handler)


def standard_error_response(status_code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"error": True, "message": message, "code": status_code},
    )


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        logger = logging.getLogger("backend.request")
        start = time.perf_counter()
        request_id = request.headers.get("x-request-id") or uuid4().hex
        request.state.request_id = request_id
        endpoint = getattr(getattr(request.scope, "get", lambda *_: None)("route"), "path", None) or request.url.path

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": endpoint,
                    "status": 500,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": endpoint,
                "status": response.status_code,
                "duration_ms": duration_ms,
            },
        )
        record_http_request(request.method, endpoint, response.status_code)
        return response