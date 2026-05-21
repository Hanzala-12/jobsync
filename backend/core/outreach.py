"""
Cold Outreach Generation with optional Hunter.io integration
"""
from core.llm_provider import LLMProvider
import requests
import os

def find_email_hunter(first_name: str, last_name: str, domain: str, api_key=None) -> str:
    """Find email using Hunter.io API (optional)"""
    api_key = api_key or os.getenv("HUNTER_API_KEY")
    
    if not api_key:
        return None
    
    try:
        url = f"https://api.hunter.io/v2/email-finder"
        params = {
            "domain": domain,
            "first_name": first_name,
            "last_name": last_name,
            "api_key": api_key
        }
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        
        if data.get("data") and data["data"].get("email"):
            return data["data"]["email"]
    except Exception as e:
        print(f"Hunter.io error: {e}")
    
    return None

def generate_linkedin_message(company: str, role: str, resume_text: str, llm: LLMProvider = None) -> str:
    """Generate LinkedIn outreach message"""
    if llm is None:
        llm = LLMProvider()
    
    prompt = f"""Write a concise, professional LinkedIn outreach message to a recruiter at {company} about the {role} position. 

Mention your fit based on: {resume_text[:1000]}

Keep it under 150 words, friendly but professional."""
    
    return llm.ask("You are a job seeker writing a networking message.", prompt)

def generate_cold_email(company: str, role: str, resume_text: str, recipient_email: str = None, llm: LLMProvider = None) -> str:
    """Generate cold outreach email"""
    if llm is None:
        llm = LLMProvider()
    
    prompt = f"""Write a professional cold outreach email for the {role} position at {company}.

Your background: {resume_text[:1000]}

Include:
- Subject line
- Brief introduction
- Why you're interested
- Call to action

Keep it concise and professional."""
    
    return llm.ask("You are a job seeker writing a cold email.", prompt)
