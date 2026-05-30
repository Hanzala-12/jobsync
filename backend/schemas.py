from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: str
    password: str
    name: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(ORMBase):
    id: int
    email: str
    name: Optional[str] = None
    is_active: bool
    token_version: int = 0
    created_at: datetime


class AuthToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


class LogoutResponse(BaseModel):
    success: bool = True


class UserApiKeyStatus(BaseModel):
    provider: str
    has_key: bool


class UserApiKeyUpsertRequest(BaseModel):
    provider: str
    api_key: str


class UserApiKeyDeleteResponse(BaseModel):
    success: bool = True


class ResumeAnalysis(BaseModel):
    ats_score: float
    matched_skills: List[str]
    missing_keywords: List[str]
    tips: List[str]
    resume_text: Optional[str] = None


class ResumeReanalysisRequest(BaseModel):
    job_description: str


class ResumeRewriteRequest(BaseModel):
    resume_text: str
    job_description: str
    job_type: str = "General"


class ResumeRewriteResponse(BaseModel):
    rewritten: str
    changes_made: List[str]
    keywords_added: List[str]
    keywords_removed: List[str]


class ResumeBuildResponse(BaseModel):
    original_resume: str
    simple_text_version: str
    fixed_resume_text: str
    sections: Dict[str, object] = Field(default_factory=dict)
    keyword_debug: Dict[str, object] = Field(default_factory=dict)
    ats_score: int = Field(ge=0, le=100)
    changes_made: List[str]
    html_resume: str
    validation_passed: bool
    validation_message: str
    cached: bool = False


class UserEducationBase(BaseModel):
    degree: Optional[str] = None
    institution: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    gpa: Optional[str] = None
    description: Optional[str] = None


class UserEducationCreate(UserEducationBase):
    pass


class UserEducationOut(ORMBase):
    id: int
    degree: Optional[str] = None
    institution: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    gpa: Optional[str] = None
    description: Optional[str] = None


class UserWorkExperienceBase(BaseModel):
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)


class UserWorkExperienceCreate(UserWorkExperienceBase):
    pass


class UserWorkExperienceOut(ORMBase):
    id: int
    job_title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    responsibilities: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)


class UserCertificationBase(BaseModel):
    name: Optional[str] = None
    issuing_org: Optional[str] = None
    date_earned: Optional[str] = None
    credential_url: Optional[str] = None


class UserCertificationCreate(UserCertificationBase):
    pass


class UserCertificationOut(ORMBase):
    id: int
    name: Optional[str] = None
    issuing_org: Optional[str] = None
    date_earned: Optional[str] = None
    credential_url: Optional[str] = None


class UserProjectBase(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    project_url: Optional[str] = None


class UserProjectCreate(UserProjectBase):
    pass


class UserProjectOut(ORMBase):
    id: int
    name: Optional[str] = None
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    project_url: Optional[str] = None


class UserLanguageBase(BaseModel):
    name: Optional[str] = None
    proficiency: Optional[str] = None


class UserLanguageCreate(UserLanguageBase):
    pass


class UserLanguageOut(ORMBase):
    id: int
    name: Optional[str] = None
    proficiency: Optional[str] = None


class UserProfileBase(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    preferred_job_titles: List[str] = Field(default_factory=list)
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    willing_to_relocate: bool = False
    preferred_work_location: Optional[str] = None
    resume_text: Optional[str] = None


class UserProfileCreate(UserProfileBase):
    education: List[UserEducationCreate] = Field(default_factory=list)
    work_experience: List[UserWorkExperienceCreate] = Field(default_factory=list)
    certifications: List[UserCertificationCreate] = Field(default_factory=list)
    projects: List[UserProjectCreate] = Field(default_factory=list)
    languages: List[UserLanguageCreate] = Field(default_factory=list)


class UserProfileUpdate(UserProfileCreate):
    pass


class UserProfileOut(ORMBase):
    id: int
    user_id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    achievements: List[str] = Field(default_factory=list)
    preferred_job_titles: List[str] = Field(default_factory=list)
    desired_salary_min: Optional[int] = None
    desired_salary_max: Optional[int] = None
    willing_to_relocate: bool = False
    preferred_work_location: Optional[str] = None
    resume_text: Optional[str] = None
    latest_ats_score: Optional[float] = None
    created_at: datetime
    education: List[UserEducationOut] = Field(default_factory=list)
    work_experience: List[UserWorkExperienceOut] = Field(default_factory=list)
    certifications: List[UserCertificationOut] = Field(default_factory=list)
    projects: List[UserProjectOut] = Field(default_factory=list)
    languages: List[UserLanguageOut] = Field(default_factory=list)
    profile_completeness: Optional[int] = None


class UserProfileSummary(ORMBase):
    id: int
    user_id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    location: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    preferred_job_titles: List[str] = Field(default_factory=list)
    latest_ats_score: Optional[float] = None
    created_at: datetime
    profile_completeness: Optional[int] = None


class UserProfileListResponse(BaseModel):
    profiles: List[UserProfileSummary] = Field(default_factory=list)
    selected_profile_id: Optional[int] = None
    selected_profile: Optional[UserProfileOut] = None


class ResumeVersionCreate(BaseModel):
    name: str
    job_type: str
    content: str
    used_for: Optional[str] = None
    ats_score: Optional[int] = None


class ResumeVersionUpdateUsedFor(BaseModel):
    used_for: Optional[str] = None


class ResumeVersionOut(ORMBase):
    id: int
    name: str
    job_type: str
    content: str
    created_at: datetime
    used_for: Optional[str]
    ats_score: Optional[int]


class JobOut(ORMBase):
    id: int
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str
    posted_date: Optional[str] = None
    salary: Optional[str] = None


class JobUpsert(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    apply_url: Optional[str] = None
    source: Optional[str] = None
    external_id: Optional[str] = None
    location: Optional[str] = None
    city: Optional[str] = None
    posted_date: Optional[str] = None
    salary: Optional[str] = None
    job_type: Optional[str] = None
    experience_required: Optional[str] = None


class ExplainMatchRequest(BaseModel):
    job_description: str
    resume_text: str


class JobMatchExplainRequest(ExplainMatchRequest):
    pass


class JobMatch(BaseModel):
    job_id: int
    match_percentage: float
    explanation: str
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str]


class JobMatchExplainRequest(BaseModel):
    job_description: str
    resume_text: str


class JobMatchExplainResponse(BaseModel):
    paragraph1: str
    paragraph2: str
    paragraph3: str
    match_score: int = Field(ge=0, le=100)
    matched_skills: List[str]
    missing_skills: List[str]
    quick_win: str


class ApiErrorResponse(BaseModel):
    error: bool = True
    message: str
    code: int


class HealthResponse(BaseModel):
    status: str
    database: str


class SalaryEstimateRequest(BaseModel):
    title: str
    location: str = "Pakistan"
    experience_level: str
    skills: List[str] = []


class SalaryEstimateResponse(BaseModel):
    local_min: int
    local_max: int
    remote_min: int
    remote_max: int
    market_demand: str
    negotiation_tip: str
    top_paying_companies: List[str]


class InterviewPredictRequest(BaseModel):
    job_description: str
    resume_text: str
    company: str
    role: str


class InterviewPredictedQuestion(BaseModel):
    question: str
    why_asked: str
    strong_answer_includes: List[str]
    difficulty: str
    type: str


class ApplicationCreate(BaseModel):
    job_id: Optional[int] = None
    company: str
    role: str
    status: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    resume_version: Optional[str] = None
    contact_email: Optional[str] = None
    next_action: Optional[str] = None


class ApplicationOut(ORMBase):
    id: int
    job_id: Optional[int]
    company: str
    role: str
    applied_date: datetime
    interview_date: Optional[datetime]
    follow_up_date: Optional[datetime]
    status: str
    source: Optional[str]
    next_action: Optional[str]
    notes: Optional[str]
    resume_version: Optional[str]
    contact_email: Optional[str]


class ApplicationUpdate(BaseModel):
    company: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    source: Optional[str] = None
    notes: Optional[str] = None
    resume_version: Optional[str] = None
    contact_email: Optional[str] = None
    interview_date: Optional[datetime] = None
    follow_up_date: Optional[datetime] = None
    next_action: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str


class HealthScoreResponse(BaseModel):
    score: int
    grade: str
    status_message: str
    deductions: List[str]
    improvements: List[str]
    streak: int


class CoverLetterRequest(BaseModel):
    job_description: str
    company: str
    role: str
    tone: Optional[str] = "professional"


class CoverLetterResponse(BaseModel):
    draft: str
    source_ids: List[str] = Field(default_factory=list)


class SkillGapRequest(BaseModel):
    job_descriptions: List[str]


class SkillGapResponse(BaseModel):
    missing_skills: List[str]
    frequency: Dict[str, int]


class InterviewPrepRequest(BaseModel):
    role: str
    job_description: Optional[str] = None


class InterviewQuestion(BaseModel):
    question: str
    suggested_answer: Optional[str] = None


class InterviewPrepResponse(BaseModel):
    questions: List[InterviewQuestion]

