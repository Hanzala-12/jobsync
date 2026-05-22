from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ORMBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class UserOut(ORMBase):
    id: int
    email: str
    is_active: bool
    created_at: datetime


class AuthToken(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserOut


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


class UniversityBase(BaseModel):
    name: str
    country: str
    city: str
    website: Optional[str] = None
    ranking: Optional[str] = None
    ranking_global: Optional[int] = None
    logo_url: Optional[str] = None
    acceptance_rate: Optional[float] = None
    accreditation: Optional[str] = None
    student_population: Optional[int] = None


class UniversityCreate(UniversityBase):
    pass


class UniversityOut(ORMBase):
    id: int
    name: str
    country: str
    city: str
    website: Optional[str] = None
    ranking: Optional[str] = None
    ranking_global: Optional[int] = None
    logo_url: Optional[str] = None
    acceptance_rate: Optional[float] = None
    accreditation: Optional[str] = None
    student_population: Optional[int] = None


class ProgramBase(BaseModel):
    university_id: int
    name: str
    degree_level: str
    duration_years: int
    estimated_tuition_fees: int
    currency: str
    min_gpa: Optional[float] = None
    ranking_global: Optional[int] = None
    ranking_national: Optional[int] = None
    min_ielts: Optional[float] = None
    min_toefl: Optional[int] = None
    application_deadline: Optional[str] = None
    semester_intake: Optional[str] = None
    living_cost_estimate: Optional[int] = None
    scholarship_available: bool = False
    program_url: Optional[str] = None


class ProgramCreate(ProgramBase):
    pass


class ProgramOut(ORMBase):
    id: int
    university_id: int
    name: str
    degree_level: str
    duration_years: int
    estimated_tuition_fees: int
    currency: str
    min_gpa: Optional[float] = None
    ranking_global: Optional[int] = None
    ranking_national: Optional[int] = None
    min_ielts: Optional[float] = None
    min_toefl: Optional[int] = None
    application_deadline: Optional[str] = None
    semester_intake: Optional[str] = None
    living_cost_estimate: Optional[int] = None
    scholarship_available: bool = False
    program_url: Optional[str] = None


class StudentProfileBase(BaseModel):
    gpa: float
    gre_score: Optional[int] = None
    toefl_score: Optional[int] = None
    ielts_score: Optional[float] = None
    budget_per_year: int
    preferred_countries: List[str] = Field(default_factory=list)
    intended_major: str
    degree_level: str
    academic_background: Optional[str] = None


class StudentProfileCreate(StudentProfileBase):
    pass


class StudentProfileOut(ORMBase):
    id: int
    gpa: float
    gre_score: Optional[int] = None
    toefl_score: Optional[int] = None
    ielts_score: Optional[float] = None
    budget_per_year: int
    preferred_countries: List[str]
    intended_major: str
    degree_level: str
    academic_background: Optional[str] = None
    created_at: Optional[datetime] = None


class UniversityRecommendationRequest(BaseModel):
    student_profile_id: int
    intended_major: str


class UniversityRecommendationItem(BaseModel):
    university: UniversityOut
    program: ProgramOut
    match_score: int
    explanation: str
    cached: bool = False
    cache_expires_at: Optional[datetime] = None


class UniversityRecommendationResponse(BaseModel):
    student_profile: StudentProfileOut
    recommendations: List[UniversityRecommendationItem]


class ScholarshipBase(BaseModel):
    name: str
    university_id: int
    amount_usd: Optional[int] = None
    deadline: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    application_url: Optional[str] = None


class ScholarshipCreate(ScholarshipBase):
    pass


class ScholarshipOut(ORMBase):
    id: int
    name: str
    university_id: int
    amount_usd: Optional[int] = None
    deadline: Optional[str] = None
    eligibility_criteria: Optional[str] = None
    application_url: Optional[str] = None


class UniversityProgramGroup(BaseModel):
    university: UniversityOut
    programs: List[ProgramOut]


class UniversityFilterResponse(BaseModel):
    page: int
    limit: int
    total: int
    items: List[UniversityProgramGroup]


class UniversityDetailResponse(BaseModel):
    university: UniversityOut
    programs: List[ProgramOut]
    scholarships: List[ScholarshipOut]


class StudentProfileUpdate(BaseModel):
    gpa: Optional[float] = None
    gre_score: Optional[int] = None
    toefl_score: Optional[int] = None
    ielts_score: Optional[float] = None
    budget_per_year: Optional[int] = None
    preferred_countries: Optional[List[str]] = None
    intended_major: Optional[str] = None
    degree_level: Optional[str] = None
    academic_background: Optional[str] = None


class StudentProgramMatchBase(BaseModel):
    student_id: int
    program_id: int
    match_score: int
    academic_fit: int
    budget_fit: int
    location_fit: int
    missing_requirements: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    summary: str
    computed_at: datetime
    expires_at: datetime


class StudentProgramMatchOut(ORMBase):
    id: int
    student_id: int
    program_id: int
    match_score: int
    academic_fit: int
    budget_fit: int
    location_fit: int
    missing_requirements: List[str]
    strengths: List[str]
    recommendations: List[str]
    summary: str
    computed_at: datetime
    expires_at: datetime


class UniversityMatchRecommendRequest(BaseModel):
    student_profile_id: int
    limit: int = 20
    min_match_score: int = 0
    sort_by: str = "match_score"
    filter_countries: List[str] = Field(default_factory=list)
    filter_max_tuition: Optional[int] = None
    filter_scholarship_only: bool = False


class UniversityMatchProgramItem(BaseModel):
    university: UniversityOut
    program: ProgramOut
    vector_similarity: int
    match: StudentProgramMatchOut
    cached: bool = False


class UniversityMatchRecommendResponse(BaseModel):
    student_profile: StudentProfileOut
    results: List[UniversityMatchProgramItem]


class UniversityMatchDetailResponse(BaseModel):
    student_profile: StudentProfileOut
    university: UniversityOut
    program: ProgramOut
    match: StudentProgramMatchOut
    analysis: Dict[str, object]


class StudentSaveRequest(BaseModel):
    student_id: int
    program_id: int


class SavedProgramOut(ORMBase):
    id: int
    student_id: int
    program_id: int
    saved_at: datetime
    program: Optional[ProgramOut] = None
    university: Optional[UniversityOut] = None


class StudentApplyRequest(BaseModel):
    student_id: int
    program_id: int
    notes: Optional[str] = None


class StudyApplicationUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class StudyApplicationOut(ORMBase):
    id: int
    student_id: int
    program_id: int
    status: str
    notes: Optional[str] = None
    applied_at: Optional[datetime] = None
    deadline: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    program: Optional[ProgramOut] = None
    university: Optional[UniversityOut] = None
