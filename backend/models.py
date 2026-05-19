from sqlalchemy import Column, Integer, String, Text, Float, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from backend.database import Base
import enum

class ApplicationStatus(str, enum.Enum):
    SAVED = "Saved"
    APPLIED = "Applied"
    INTERVIEWING = "Interviewing"
    OFFERED = "Offered"
    REJECTED = "Rejected"

class UserProfile(Base):
    __tablename__ = "user_profiles"
    id = Column(Integer, primary_key=True, index=True)
    resume_text = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)          # comma-separated
    latest_ats_score = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)
    external_id = Column(String, unique=True)      # unique across sources
    title = Column(String)
    company = Column(String)
    location = Column(String)
    description = Column(Text)
    url = Column(String)
    posted_date = Column(String, nullable=True)
    fetched_at = Column(DateTime, server_default=func.now())

class Application(Base):
    __tablename__ = "applications"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=True)        # FK to jobs.id (optional)
    company = Column(String)
    role = Column(String)
    source = Column(String, nullable=True)
    applied_date = Column(DateTime, server_default=func.now())
    interview_date = Column(DateTime, nullable=True)
    follow_up_date = Column(DateTime, nullable=True)
    status = Column(String, default=ApplicationStatus.SAVED.value)
    next_action = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    resume_version = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
