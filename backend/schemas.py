from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


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


class ScoutRequest(BaseModel):
    role: str = "software engineer"
    location: str = "Pakistan"
    skills: str = ""
    min_score: int = 75
    page: int = 1


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


class JobMatch(BaseModel):
    job_id: int
    match_percentage: float
    explanation: str
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
