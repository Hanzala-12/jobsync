import logging
import os
import json
import time
from collections import defaultdict, deque
from typing import Deque, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy import inspect

from backend.database import engine, Base
from backend.routers import resume, jobs, applications, cover_letter, intelligence, student
from backend.routers import kanban, voice_interview, browser_extension, followup
import importlib
profile = importlib.import_module('backend.routers.profile')
from core.scheduler import start_scheduler_if_enabled
from alembic.config import Config
from alembic import command
from backend.middleware.logging import RequestLoggingMiddleware, configure_logging, standard_error_response
from backend.routers.jobs import shutdown_background_executor

configure_logging()
logger = logging.getLogger(__name__)

REQUIRED_TABLES = [
    "jobs",
    "applications",
    "resume_versions",
    "prefetched_jobs",
    "user_profiles",
    "user_preferences",
    "universities",
    "programs",
    "student_profiles",
    "scholarships",
    "saved_programs",
    "applications_study",
    "student_program_matches",
    "university_match_cache",
]

REQUIRED_UNIVERSITY_COLUMNS = ["created_at", "updated_at", "last_scraped_at"]


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, limit: int, period: int):
        super().__init__(app)
        self.limit = max(1, limit)
        self.period = max(1, period)
        self._requests: Dict[str, Deque[float]] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path.startswith(("/docs", "/redoc", "/openapi")):
            return await call_next(request)

        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        now = time.time()
        bucket = self._requests[client_ip]
        cutoff = now - self.period
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return standard_error_response(429, "Rate limit exceeded")
        bucket.append(now)
        return await call_next(request)


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        return ["*"]
    if raw.startswith("["):
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            pass
    return [origin.strip() for origin in raw.split(",") if origin.strip()]

def _verify_required_tables() -> None:
    inspector = inspect(engine)
    missing_tables = [table_name for table_name in REQUIRED_TABLES if not inspector.has_table(table_name)]
    if missing_tables:
        raise RuntimeError(f"Missing required database tables: {', '.join(missing_tables)}")


def _warn_if_university_columns_missing() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("universities"):
        return

    existing_columns = {column["name"] for column in inspector.get_columns("universities")}
    missing_columns = [column_name for column_name in REQUIRED_UNIVERSITY_COLUMNS if column_name not in existing_columns]
    if missing_columns:
        logger.warning(
            "universities table is missing expected columns: %s",
            ", ".join(missing_columns),
        )


def _run_startup_migrations() -> None:
    alembic_ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    if not os.path.exists(alembic_ini_path):
        alembic_ini_path = "backend/alembic.ini"
    alembic_cfg = Config(alembic_ini_path)
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception:
        logger.exception("Alembic upgrade failed; falling back to Base.metadata.create_all")
        Base.metadata.create_all(bind=engine, checkfirst=True)
    else:
        try:
            _verify_required_tables()
        except Exception:
            logger.warning("Required tables were still missing after Alembic; creating them from metadata")
            Base.metadata.create_all(bind=engine, checkfirst=True)

    _verify_required_tables()
    _warn_if_university_columns_missing()


# Initialize database / run migrations automatically on startup
try:
    _run_startup_migrations()
    print("Alembic migrations applied successfully on startup.")
except Exception:
    logger.exception("Alembic migration or schema validation failed on startup")
    raise

app = FastAPI(
    title="JobSync Pro API", 
    version="2.0.0", 
    description="AI-powered job search assistant with advanced features"
)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    SimpleRateLimitMiddleware,
    limit=int(os.getenv("RATE_LIMIT_REQUESTS", "100")),
    period=int(os.getenv("RATE_LIMIT_PERIOD", "60")),
)

app.add_middleware(RequestLoggingMiddleware)

# Include original routers
app.include_router(resume.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(cover_letter.router)
app.include_router(intelligence.router)
app.include_router(student.router)
app.include_router(student.api_router)
app.include_router(profile.router)

# Include new upgrade routers
app.include_router(kanban.router)
app.include_router(voice_interview.router)
app.include_router(browser_extension.router)
app.include_router(followup.router)
try:
    from backend.routers import daily_scout
    app.include_router(daily_scout.router)
except Exception:
    logger.exception("daily_scout router unavailable; continuing without it")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return standard_error_response(exc.status_code, message)


@app.exception_handler(StarletteHTTPException)
async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return standard_error_response(exc.status_code, message)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    message = "; ".join(error.get("msg", "Invalid request") for error in exc.errors()) or "Invalid request"
    return standard_error_response(422, message)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled exception during request %s %s", request.method, request.url.path)
    return standard_error_response(500, "Internal server error")


@app.on_event("startup")
def startup_scheduler():
    if (
        not os.getenv("OPENROUTER_API_KEY", "").strip()
        and not os.getenv("OPENROUTER_API_KEY_2", "").strip()
        and not os.getenv("OPENAI_API_KEY", "").strip()
        and not os.getenv("OPENAI_API_KEY_2", "").strip()
        and not os.getenv("NOVITA_API_KEY", "").strip()
        and not os.getenv("NOVITA_API_KEY_2", "").strip()
        and not os.getenv("GROQ_API_KEY", "").strip()
        and not os.getenv("GROQ_API_KEY_2", "").strip()
    ):
        logger.warning("No LLM API key configured; falling back to heuristic matching where available.")
    start_scheduler_if_enabled()


@app.on_event("shutdown")
def shutdown_background_workers():
    shutdown_background_executor()


@app.get("/health")
def health_check():
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        _verify_required_tables()
        return {"status": "ok", "database": "connected"}
    except Exception:
        logger.exception("Health check database probe failed")
        raise HTTPException(status_code=503, detail="Database unavailable")

@app.get("/")
def root():
    return {
        "message": "JobSync Pro API is running",
        "version": "2.0.0",
        "docs": "/docs",
        "features": [
            "Resume Analysis",
            "Job Search & Matching",
            "Application Tracking",
            "Kanban Board",
            "Interview Practice",
            "Follow-up Agent",
            "Daily Scout",
            "Browser Extension Support",
            "PDF Generation",
            "Salary Negotiation"
        ]
    }

