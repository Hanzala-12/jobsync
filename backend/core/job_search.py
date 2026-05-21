"""
Automated Job Hunting - JSearch API Integration
"""
import requests
import os
from typing import List, Optional
from core.geo import validate_and_normalize_location

def search_jobs_jsearch(query: str, location_raw: str = "", api_key: Optional[str] = None) -> List[dict]:
    """Search jobs using JSearch (RapidAPI) with location validation"""
    api_key = api_key or os.getenv("RAPIDAPI_KEY")
    
    if not api_key:
        # Fallback to empty list if no API key
        return []
    
    # Normalize location
    location_str = ""
    if location_raw:
        # Expect input like "Lahore, Pakistan" or just "Pakistan"
        parts = [p.strip() for p in location_raw.split(',')]
        city_part = parts[0] if len(parts) > 0 else ""
        country_part = parts[1] if len(parts) > 1 else ""
        loc = validate_and_normalize_location(city_part, country_part)
        location_str = loc["full_location"]
    
    # Build query
    full_query = query
    if location_str:
        full_query += f" in {location_str}"
    
    url = "https://jsearch.p.rapidapi.com/search"
    headers = {
        "X-RapidAPI-Key": api_key,
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com"
    }
    
    params = {
        "query": full_query,
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
