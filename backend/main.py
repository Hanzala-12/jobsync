from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routers import resume, jobs, applications, cover_letter, intelligence
from backend.routers import kanban, voice_interview, browser_extension, followup, daily_scout
import importlib
profile = importlib.import_module('backend.routers.profile')
from core.scheduler import start_scheduler_if_enabled
import os
from alembic.config import Config
from alembic import command

# Initialize database / run migrations automatically on startup
try:
    alembic_ini_path = os.path.join(os.path.dirname(__file__), "alembic.ini")
    if not os.path.exists(alembic_ini_path):
        alembic_ini_path = "backend/alembic.ini"
    alembic_cfg = Config(alembic_ini_path)
    command.upgrade(alembic_cfg, "head")
    print("Alembic migrations applied successfully on startup.")
except Exception as e:
    print(f"Alembic migration failed on startup: {e}")

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
app.include_router(daily_scout.router)


@app.on_event("startup")
def startup_scheduler():
    start_scheduler_if_enabled()

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

