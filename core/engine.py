"""
JobAnalyser Engine - Core AI analysis logic
"""
from core.llm_provider import LLMProvider

class JobAnalyser:
    def __init__(self, llm: LLMProvider = None):
        self.llm = llm or LLMProvider()
    
    def analyse_job(self, job_text: str) -> dict:
        """Extract skills and requirements from job description"""
        prompt = f"""Analyze this job description and extract:
1. Required technical skills
2. Required soft skills
3. Key responsibilities
4. Nice-to-have skills

Job Description:
{job_text[:2000]}

Return as structured text."""
        
        analysis = self.llm.ask("You are a job analysis expert.", prompt)
        return {"raw_analysis": analysis, "job_text": job_text[:2000]}
    
    def analyse_resume(self, resume_text: str) -> dict:
        """Extract skills and experience from resume"""
        prompt = f"""Analyze this resume and extract:
1. Technical skills
2. Soft skills
3. Key projects and achievements
4. Years of experience

Resume:
{resume_text[:2000]}

Return as structured text."""
        
        analysis = self.llm.ask("You are a resume analysis expert.", prompt)
        return {"raw_analysis": analysis, "resume_text": resume_text[:2000]}
    
    def match(self, job_analysis: dict, resume_analysis: dict) -> dict:
        """Calculate match score between job and resume"""
        prompt = f"""Compare this job requirement with the candidate's resume:

Job Requirements:
{job_analysis['raw_analysis']}

Candidate Resume:
{resume_analysis['raw_analysis']}

Provide:
1. Match score (0-100)
2. Matched skills
3. Missing skills
4. Brief explanation"""
        
        result = self.llm.ask("You are a hiring expert.", prompt)
        
        # Parse score from result (simple extraction)
        score = 75  # default
        if "score" in result.lower():
            import re
            match = re.search(r'(\d+)(?:/100|%|\s+out of 100)', result, re.IGNORECASE)
            if match:
                score = int(match.group(1))
        
        return {
            "score": score,
            "analysis": result,
            "matched": [],
            "missing": []
        }
    
    def score_and_filter_jobs(self, resume_analysis: dict, jobs: list, min_score=70) -> list:
        """Score multiple jobs against resume and filter by minimum score"""
        results = []
        for job in jobs:
            analysis = self.analyse_job(job.get('description', ''))
            match = self.match(analysis, resume_analysis)
            if match['score'] >= min_score:
                job['match_score'] = match['score']
                job['missing_skills'] = match['missing']
                job['match_analysis'] = match['analysis']
                results.append(job)
        return sorted(results, key=lambda x: x['match_score'], reverse=True)
    
    def negotiate_salary(self, job_title: str, location: str, match_score: float, 
                        salary_insight: dict, resume_text: str) -> str:
        """Generate salary negotiation script"""
        prompt = f"""You're a candidate for {job_title} in {location}. 
Market average is {salary_insight.get('average', 'unknown')} with range {salary_insight.get('range', 'unknown')}. 
Your match with the job is {match_score}%. 

Your resume strengths: {resume_text[:1000]}

Write a polite, confident salary negotiation email. Include a specific number and justification."""
        
        return self.llm.ask("You are a negotiation expert.", prompt)
