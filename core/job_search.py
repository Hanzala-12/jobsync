"""
Automated Job Hunting - JSearch API Integration
"""
import requests
import os
from typing import List, Optional

def search_jobs_jsearch(query: str, location: str = "", api_key: Optional[str] = None) -> List[dict]:
    """Search jobs using JSearch (RapidAPI)"""
    api_key = api_key or os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        # Fallback to empty list if no API key
        return []
    
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    params = {
        "query": f"{query} in {location}" if location else query,
        "page": "1",
        "num_pages": "1",
        "date_posted": "week"
    }
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json().get("data", [])
        
        jobs = []
        for j in data:
            jobs.append({
                "id": j.get("job_id"),
                "title": j.get("job_title"),
                "company": j.get("employer_name"),
                "location": f"{j.get('job_city', '')}, {j.get('job_country', '')}",
                "description": j.get("job_description", ""),
                "url": j.get("job_apply_link"),
                "posted": j.get("job_posted_at_datetime_utc")
            })
        return jobs
    except Exception as e:
        print(f"JSearch API error: {e}")
        return []

def parse_location(user_input: str) -> dict:
    """Parse location string into city and country"""
    parts = [p.strip() for p in user_input.split(',')]
    if len(parts) == 2:
        return {"city": parts[0], "country": parts[1]}
    return {"city": user_input, "country": ""}
