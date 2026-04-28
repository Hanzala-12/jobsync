from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# Resume analysis
class ResumeAnalysis(BaseModel):
    ats_score: float
    missing_keywords: List[str]
    tips: List[str]

# Job
class JobOut(BaseModel):
    id: int
    title: str
    company: str
    location: str
    description: str
    url: str
    source: str

class JobMatch(BaseModel):
    job_id: int
    match_percentage: float
    explanation: str
    missing_skills: List[str]

# Application
class ApplicationCreate(BaseModel):
    job_id: Optional[int] = None
    company: str
    role: str
    notes: Optional[str] = None
    resume_version: Optional[str] = None
    contact_email: Optional[str] = None

class ApplicationOut(BaseModel):
    id: int
    job_id: Optional[int]
    company: str
    role: str
    applied_date: datetime
    status: str
    notes: Optional[str]
    resume_version: Optional[str]

class StatusUpdate(BaseModel):
    status: str

# Cover Letter
class CoverLetterRequest(BaseModel):
    job_description: str
    company: str
    role: str

class CoverLetterResponse(BaseModel):
    draft: str

# Skill Gap
class SkillGapRequest(BaseModel):
    job_descriptions: List[str]

class SkillGapResponse(BaseModel):
    missing_skills: List[str]
    frequency: dict

# Interview Prep
class InterviewPrepRequest(BaseModel):
    role: str
    job_description: Optional[str] = None

class InterviewQuestion(BaseModel):
    question: str
    suggested_answer: str = None

class InterviewPrepResponse(BaseModel):
    questions: List[InterviewQuestion]
