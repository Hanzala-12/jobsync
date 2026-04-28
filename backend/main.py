from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base
from backend.routers import resume, jobs, applications, cover_letter, intelligence

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="JobSync API", version="1.0.0", description="AI-powered job search assistant")

# Allow frontend calls
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(resume.router)
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(cover_letter.router)
app.include_router(intelligence.router)

@app.get("/")
def root():
    return {
        "message": "JobSync API is running",
        "docs": "/docs",
        "version": "1.0.0"
    }
