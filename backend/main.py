import logging
import os

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.database import engine, Base
from backend.routers import resume, jobs, applications, cover_letter, intelligence
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

# Initialize database / run migrations automatically on startup
try:
    alembic_ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    if not os.path.exists(alembic_ini_path):
        alembic_ini_path = "backend/alembic.ini"
    alembic_cfg = Config(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")
    print("Alembic migrations applied successfully on startup.")
except Exception as e:
    logger.exception("Alembic migration failed on startup")

app = FastAPI(
    title="JobSync Pro API", 
    version="2.0.0", 
    description="AI-powered job search assistant with advanced features"
)

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

# Include original routers
app.include_router(resume.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(cover_letter.router)
app.include_router(intelligence.router)
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
    if not os.getenv("OPENROUTER_API_KEY", "").strip() and not os.getenv("GROQ_API_KEY", "").strip():
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

