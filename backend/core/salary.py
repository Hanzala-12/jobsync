"""
Salary Insights and Negotiation
"""
import json
import os

# Static salary database (expand as needed)
SALARY_DB = {
    "software engineer, lahore, pakistan": {
        "average": 120000, 
        "range": "80,000 - 180,000 PKR/month"
    },
    "software engineer, remote": {
        "average": 110000, 
        "range": "90,000 - 150,000 USD/year"
    },
    "data scientist, remote": {
        "average": 120000, 
        "range": "100,000 - 160,000 USD/year"
    },
    "frontend developer, karachi, pakistan": {
        "average": 100000, 
        "range": "70,000 - 150,000 PKR/month"
    },
    "backend developer, islamabad, pakistan": {
        "average": 130000, 
        "range": "90,000 - 200,000 PKR/month"
    },
}

def get_salary_insight(job_title: str, location: str) -> dict:
    """Get salary insights for a job title and location"""
    key = f"{job_title.lower()}, {location.lower()}"
    
    # Exact match
    if key in SALARY_DB:
        return SALARY_DB[key]
    
    # Partial match
    for k, v in SALARY_DB.items():
        if job_title.lower() in k or location.lower() in k:
            return v
    
    # Default
    return {
        "average": "market rate", 
        "range": "unknown - contact recruiter for details"
    }

def generate_negotiation_script(job_title: str, location: str, match_score: float, 
                               resume_text: str, llm) -> str:
    """Generate salary negotiation script"""
    from core.engine import JobAnalyser
    
    insight = get_salary_insight(job_title, location)
    engine = JobAnalyser(llm)
    
    return engine.negotiate_salary(job_title, location, match_score, insight, resume_text)
