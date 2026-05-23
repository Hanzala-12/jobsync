"""Structured JSON logging for production environments."""

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class JSONLogFormatter(logging.Formatter):
    """Format log records as JSON for production consumption."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id

        if record.exc_info:
            payload["exception"] = traceback.format_exception(*record.exc_info)

        for key, value in record.__dict__.items():
            if key not in {
                "args",
                "created",
                "exc_info",
                "exc_text",
                "filename",
                "funcName",
                "levelname",
                "levelno",
                "lineno",
                "module",
                "msecs",
                "message",
                "msg",
                "name",
                "pathname",
                "process",
                "processName",
                "relativeCreated",
                "stack_info",
                "thread",
                "threadName",
            }:
                payload[key] = value

        return json.dumps(payload, default=str)


def configure_structured_logging() -> None:
    """Configure root logger to emit JSON in production."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONLogFormatter())

    root = logging.getLogger()
    root.handlers = []
    root.addHandler(handler)
    root.setLevel(logging.INFO)
