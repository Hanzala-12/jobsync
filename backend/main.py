import logging
import os
import json
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy import inspect

try:
    from redis.asyncio import from_url as redis_from_url
except Exception:  # pragma: no cover - optional dependency in lightweight test envs
    redis_from_url = None

from backend.database import engine, Base
from backend.routers import resume, jobs, applications, cover_letter, intelligence, auth
from backend.routers import tasks as tasks_router
from backend.routers import kanban, voice_interview, browser_extension, followup
import importlib
profile = importlib.import_module('backend.routers.profile')
from core.scheduler import start_scheduler_if_enabled
from alembic.config import Config
from alembic import command
from backend.celery_app import configure_celery
from backend.middleware.logging import RequestLoggingMiddleware, configure_logging, standard_error_response
from backend.middleware.security import HTTPSRedirectMiddleware
from backend.middleware.ab_testing import ABTestingAssignmentMiddleware
from backend.routers.jobs import shutdown_background_executor
from backend.monitoring import ENABLE_METRICS, metrics_payload, record_http_request
from backend.security import decode_token

configure_logging()
logger = logging.getLogger(__name__)

REQUIRED_TABLES = [
    "jobs",
    "applications",
    "resume_versions",
    "prefetched_jobs",
    "user_profiles",
    "user_educations",
    "user_work_experiences",
    "user_certifications",
    "user_projects",
    "user_languages",
    "user_preferences",
    
    "ab_tests",
    "ab_test_assignments",
    "ab_test_events",
]

RUN_STARTUP_MIGRATIONS = os.getenv("RUN_STARTUP_MIGRATIONS", "false").lower() == "true"
REDIS_URL = (os.getenv("REDIS_URL") or os.getenv("CELERY_BROKER_URL") or "redis://localhost:6379/0").strip()
RATE_LIMIT_REQUESTS = max(1, int(os.getenv("RATE_LIMIT_REQUESTS", "100")))
RATE_LIMIT_PERIOD = max(1, int(os.getenv("RATE_LIMIT_PERIOD", "60")))


class RedisRateLimitMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive=receive)
        redis_client = getattr(request.app.state, "redis_client", None)
        if redis_client is None:
            await self.app(scope, receive, send)
            return

        path = request.url.path
        if path.startswith(("/docs", "/redoc", "/openapi", "/metrics")):
            await self.app(scope, receive, send)
            return

        key = self._limit_key(request)
        try:
            current = await redis_client.incr(key)
            if current == 1:
                await redis_client.expire(key, RATE_LIMIT_PERIOD)
            if current > RATE_LIMIT_REQUESTS:
                response = standard_error_response(429, "Rate limit exceeded")
                await response(scope, receive, send)
                return
        except Exception:
            logger.warning("Redis rate limiting unavailable; allowing request through", exc_info=True)

        await self.app(scope, receive, send)

    def _limit_key(self, request: Request) -> str:
        token = ""
        auth_header = request.headers.get("authorization", "")
        if auth_header.lower().startswith("bearer "):
            token = auth_header.split(" ", 1)[1].strip()
        if not token:
            token = (request.query_params.get("token") or "").strip()

        if token:
            try:
                payload = decode_token(token)
                if payload.get("type") == "access":
                    subject = str(payload.get("sub") or "")
                    token_version = str(payload.get("ver", 0) or 0)
                    if subject:
                        return f"rl:user:{subject}:{token_version}:{request.url.path}"
            except Exception:
                pass

        client_ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "unknown")
        client_ip = client_ip.split(",")[0].strip()
        return f"rl:ip:{client_ip}:{request.url.path}"


def _parse_cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS", "").strip()
    if not raw:
        logger.warning("CORS_ORIGINS not set; defaulting to no external origins. Set CORS_ORIGINS explicitly in production.")
        # Return empty list to disallow cross-origin requests by default (safe default)
        return []
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
    # University table removed from schema; no-op
    return


def _run_startup_migrations() -> None:
    if not RUN_STARTUP_MIGRATIONS:
        logger.info("Startup migrations are disabled by RUN_STARTUP_MIGRATIONS=false")
        return

    alembic_ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    if not os.path.exists(alembic_ini_path):
        alembic_ini_path = "backend/alembic.ini"
    alembic_cfg = Config(alembic_ini_path)
    # Run alembic upgrade. In some local/dev trees there may be multiple
    # migration heads (intentional during active development). Treat
    # MultipleHeads as non-fatal in dev: log and skip automatic upgrade so
    # the developer can resolve migrations manually.
    try:
        command.upgrade(alembic_cfg, "head")
    except Exception as exc:
        # Avoid crashing the app on migration conflicts in local dev
        logger.warning("Alembic upgrade skipped due to error: %s", exc)
        return

    # Verify required tables exist after migrations
    _verify_required_tables()
    _warn_if_university_columns_missing()


# Initialize database / run migrations automatically on startup
try:
    _run_startup_migrations()
    logger.info("Alembic migrations applied successfully on startup.")
except Exception:
    logger.exception("Alembic migration or schema validation failed on startup")
    raise

app = FastAPI(
    title="JobSync Pro API", 
    version="2.0.0", 
    description="AI-powered job search assistant with advanced features"
)

configure_celery(app)

app.add_middleware(GZipMiddleware, minimum_size=1000)

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_cors_origins(),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.add_middleware(
    HTTPSRedirectMiddleware,
    enabled=os.getenv("ENV", "").lower() == "production"
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(ABTestingAssignmentMiddleware)
app.add_middleware(RedisRateLimitMiddleware)

app.state.redis_client = None


@app.on_event("startup")
async def startup_redis_rate_limiter():
    if redis_from_url is None:
        logger.warning("Redis package is unavailable; distributed rate limiting is disabled")
        return

    try:
        redis_client = redis_from_url(REDIS_URL, encoding="utf-8", decode_responses=True)
        await redis_client.ping()
        app.state.redis_client = redis_client
        logger.info("Redis-backed rate limiting enabled")
    except Exception:
        logger.warning("Redis rate limiting is unavailable; proceeding without distributed throttling", exc_info=True)


@app.get("/metrics")
def metrics_endpoint():
    if not ENABLE_METRICS:
        raise HTTPException(status_code=404, detail="Metrics are disabled")
    body, content_type = metrics_payload()
    from fastapi.responses import Response

    return Response(content=body, media_type=content_type)

# Include original routers
app.include_router(resume.router)
app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(cover_letter.router)
app.include_router(intelligence.router)
app.include_router(profile.router)
app.include_router(tasks_router.api_router)

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

