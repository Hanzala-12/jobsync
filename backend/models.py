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
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    summary = Column(Text, nullable=True)
    skills = Column(JSON, nullable=False, default=list)
    achievements = Column(JSON, nullable=False, default=list)
    preferred_job_titles = Column(JSON, nullable=False, default=list)
    desired_salary_min = Column(Integer, nullable=True)
    desired_salary_max = Column(Integer, nullable=True)
    willing_to_relocate = Column(Boolean, nullable=False, default=False)
    preferred_work_location = Column(String, nullable=True)
    latest_ats_score = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    user = relationship("User")
    education = relationship("UserEducation", back_populates="profile", cascade="all, delete-orphan", order_by="UserEducation.id")
    work_experience = relationship("UserWorkExperience", back_populates="profile", cascade="all, delete-orphan", order_by="UserWorkExperience.id")
    certifications = relationship("UserCertification", back_populates="profile", cascade="all, delete-orphan", order_by="UserCertification.id")
    projects = relationship("UserProject", back_populates="profile", cascade="all, delete-orphan", order_by="UserProject.id")
    languages = relationship("UserLanguage", back_populates="profile", cascade="all, delete-orphan", order_by="UserLanguage.id")


class UserEducation(Base):
    __tablename__ = "user_educations"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    degree = Column(String, nullable=True)
    institution = Column(String, nullable=True)
    field_of_study = Column(String, nullable=True)
    start_year = Column(Integer, nullable=True)
    end_year = Column(Integer, nullable=True)
    gpa = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    profile = relationship("UserProfile", back_populates="education")


class UserWorkExperience(Base):
    __tablename__ = "user_work_experiences"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    job_title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    location = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    responsibilities = Column(JSON, nullable=False, default=list)
    achievements = Column(JSON, nullable=False, default=list)
    profile = relationship("UserProfile", back_populates="work_experience")


class UserCertification(Base):
    __tablename__ = "user_certifications"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=True)
    issuing_org = Column(String, nullable=True)
    date_earned = Column(String, nullable=True)
    credential_url = Column(String, nullable=True)
    profile = relationship("UserProfile", back_populates="certifications")


class UserProject(Base):
    __tablename__ = "user_projects"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    technologies = Column(JSON, nullable=False, default=list)
    project_url = Column(String, nullable=True)
    profile = relationship("UserProfile", back_populates="projects")


class UserLanguage(Base):
    __tablename__ = "user_languages"

    id = Column(Integer, primary_key=True, index=True)
    profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String, nullable=True)
    proficiency = Column(String, nullable=True)
    profile = relationship("UserProfile", back_populates="languages")


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    selected_profile_id = Column(Integer, ForeignKey("user_profiles.id", ondelete="SET NULL"), nullable=True)
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


class ABTest(Base):
    __tablename__ = "ab_tests"
    __table_args__ = (
        UniqueConstraint("feature_key", name="uq_ab_tests_feature_key"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    feature_key = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    traffic_split = Column(JSON, nullable=False, default=dict)
    control_algorithm_version = Column(String, nullable=False, default="v1")
    treatment_algorithm_version = Column(String, nullable=False, default="v2")
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)


class ABTestAssignment(Base):
    __tablename__ = "ab_test_assignments"
    __table_args__ = (
        UniqueConstraint("ab_test_id", "user_id", name="uq_ab_test_assignment_user"),
    )

    id = Column(Integer, primary_key=True, index=True)
    ab_test_id = Column(Integer, ForeignKey("ab_tests.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    variant = Column(String, nullable=False, index=True)
    assigned_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_seen_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    test = relationship("ABTest")
    user = relationship("User")


class ABTestEvent(Base):
    __tablename__ = "ab_test_events"

    id = Column(Integer, primary_key=True, index=True)
    ab_test_id = Column(Integer, ForeignKey("ab_tests.id", ondelete="CASCADE"), nullable=False, index=True)
    assignment_id = Column(Integer, ForeignKey("ab_test_assignments.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(Integer, nullable=True, index=True)
    program_id = Column(Integer, nullable=True, index=True)
    match_score = Column(Float, nullable=True)
    algorithm_version = Column(String, nullable=False)
    event_type = Column(String, nullable=False, index=True)
    user_clicks = Column(JSON, nullable=False, default=dict)
    event_metadata = Column(JSON, nullable=False, default=dict)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False, index=True)

    test = relationship("ABTest")
    assignment = relationship("ABTestAssignment")
    user = relationship("User")
    


Index("ix_ab_test_events_test_variant_time", ABTestEvent.ab_test_id, ABTestEvent.assignment_id, ABTestEvent.timestamp)
