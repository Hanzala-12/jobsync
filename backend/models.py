from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from backend.database import Base


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
    skills = Column(Text, nullable=True)
    latest_ats_score = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)
    external_id = Column(String, unique=True)
    title = Column(String)
    company = Column(String)
    location = Column(String)
    city = Column(String, index=True, nullable=True)
    description = Column(Text)
    url = Column(String)
    apply_url = Column(String, nullable=True)
    posted_date = Column(String, nullable=True)
    salary = Column(String, nullable=True)
    job_type = Column(String, nullable=True)
    experience_required = Column(String, nullable=True)
    scraped_at = Column(DateTime, nullable=True)
    dedup_fingerprint = Column(String, index=True, nullable=True)
    sources_seen = Column(Text, nullable=True)
    first_seen_at = Column(DateTime, default=datetime.utcnow)
    last_seen_at = Column(DateTime, default=datetime.utcnow)
    possibly_inactive = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    fetched_at = Column(DateTime, server_default=func.now())


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, nullable=True)
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


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True)
    name = Column(String)
    job_type = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_for = Column(String, nullable=True)
    ats_score = Column(Integer, nullable=True)
