from datetime import datetime
import enum

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship

from backend.database import Base


class ApplicationStatus(str, enum.Enum):
    SAVED = "Saved"
    APPLIED = "Applied"
    INTERVIEWING = "Interviewing"
    OFFERED = "Offered"
    REJECTED = "Rejected"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_text = Column(Text, nullable=True)
    skills = Column(Text, nullable=True)
    latest_ats_score = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    selected_profile_id = Column(Integer, nullable=True)
    selected_student_profile_id = Column(Integer, nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    user = relationship("User")


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
    job_skills = Column(JSON, nullable=False, default=list)
    scraped_at = Column(DateTime, nullable=True)
    dedup_fingerprint = Column(String, index=True, nullable=True)
    sources_seen = Column(Text, nullable=True)
    first_seen_at = Column(DateTime, server_default=func.now())
    last_seen_at = Column(DateTime, server_default=func.now())
    possibly_inactive = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    fetched_at = Column(DateTime, server_default=func.now())


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
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
    user = relationship("User")


class TimestampMixin:
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ResumeVersion(Base):
    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String)
    job_type = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    used_for = Column(String, nullable=True)
    ats_score = Column(Integer, nullable=True)
    user = relationship("User")


class PrefetchedJob(Base):
    __tablename__ = "prefetched_jobs"

    job_id = Column(String, primary_key=True)
    title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    source = Column(String, nullable=True)
    fetched_at = Column(DateTime, default=datetime.utcnow)


Index("ix_prefetched_fetched_at", PrefetchedJob.fetched_at)


class University(Base):
    __tablename__ = "universities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    country = Column(String, nullable=False, index=True)
    city = Column(String, nullable=False, index=True)
    website = Column(String, nullable=True)
    ranking = Column(String, nullable=True, index=True)
    ranking_global = Column(Integer, nullable=True, index=True)
    logo_url = Column(String, nullable=True)
    acceptance_rate = Column(Float, nullable=True)
    accreditation = Column(String, nullable=True)
    student_population = Column(Integer, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    last_scraped_at = Column(DateTime(timezone=True), nullable=True, index=True)

    programs = relationship("Program", back_populates="university", cascade="all, delete-orphan")
    scholarships = relationship("Scholarship", back_populates="university", cascade="all, delete-orphan")


class Program(Base):
    __tablename__ = "programs"

    id = Column(Integer, primary_key=True, index=True)
    university_id = Column(Integer, ForeignKey("universities.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=False, index=True)
    degree_level = Column(String, nullable=False, index=True)
    duration_years = Column(Integer, nullable=False)
    estimated_tuition_fees = Column(Integer, nullable=False)
    currency = Column(String(10), nullable=False)
    min_gpa = Column(Float, nullable=True)
    ranking_global = Column(Integer, nullable=True, index=True)
    ranking_national = Column(Integer, nullable=True, index=True)
    min_ielts = Column(Float, nullable=True)
    min_toefl = Column(Integer, nullable=True)
    application_deadline = Column(String, nullable=True)
    semester_intake = Column(String, nullable=True, index=True)
    living_cost_estimate = Column(Integer, nullable=True)
    scholarship_available = Column(Boolean, default=False, nullable=False)
    program_url = Column(String, nullable=True)

    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    university = relationship("University", back_populates="programs")


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    gpa = Column(Float, nullable=False)
    gre_score = Column(Integer, nullable=True)
    toefl_score = Column(Integer, nullable=True)
    ielts_score = Column(Float, nullable=True)
    budget_per_year = Column(Integer, nullable=False)
    preferred_countries = Column(JSON, nullable=False, default=list)
    intended_major = Column(String, nullable=False, index=True)
    degree_level = Column(String, nullable=False, index=True)
    academic_background = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    profile_skills = Column(JSON, nullable=False, default=list)
    user = relationship("User")



class UniversityMatchCache(Base):
    __tablename__ = "university_match_cache"
    __table_args__ = (
        UniqueConstraint("student_profile_id", "program_id", "intended_major", name="uq_university_match_cache_lookup"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_profile_id = Column(Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    intended_major = Column(String, nullable=False, index=True)
    match_score = Column(Integer, nullable=False)
    explanation = Column(Text, nullable=False)
    source_ids = Column(JSON, nullable=False, default=list)
    cached_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    student_profile = relationship("StudentProfile")
    program = relationship("Program")
    user = relationship("User")


class Scholarship(Base):
    __tablename__ = "scholarships"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False, index=True)
    university_id = Column(Integer, ForeignKey("universities.id", ondelete="CASCADE"), nullable=False, index=True)
    amount_usd = Column(Integer, nullable=True)
    deadline = Column(String, nullable=True)
    eligibility_criteria = Column(Text, nullable=True)
    application_url = Column(String, nullable=True)

    university = relationship("University", back_populates="scholarships")


class StudentProgramMatch(Base):
    __tablename__ = "student_program_matches"
    __table_args__ = (
        UniqueConstraint("student_id", "program_id", name="uq_student_program_matches_lookup"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    match_score = Column(Integer, nullable=False)
    academic_fit = Column(Integer, nullable=False)
    budget_fit = Column(Integer, nullable=False)
    location_fit = Column(Integer, nullable=False)
    missing_requirements = Column(JSON, nullable=False, default=list)
    strengths = Column(JSON, nullable=False, default=list)
    recommendations = Column(JSON, nullable=False, default=list)
    summary = Column(String(500), nullable=False)
    computed_at = Column(DateTime, server_default=func.now(), nullable=False)
    expires_at = Column(DateTime, nullable=False, index=True)

    student = relationship("StudentProfile")
    program = relationship("Program")
    user = relationship("User")


class SavedProgram(Base):
    __tablename__ = "saved_programs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    saved_at = Column(DateTime, server_default=func.now(), nullable=False)

    student = relationship("StudentProfile")
    program = relationship("Program")
    user = relationship("User")


class StudyApplication(Base):
    __tablename__ = "applications_study"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id = Column(Integer, ForeignKey("student_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    program_id = Column(Integer, ForeignKey("programs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String, nullable=False, default="saved", index=True)
    notes = Column(Text, nullable=True)
    applied_at = Column(DateTime, nullable=True)
    deadline = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    student = relationship("StudentProfile")
    program = relationship("Program")
    user = relationship("User")
