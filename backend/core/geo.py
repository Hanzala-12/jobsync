"""
Geographic location validation and normalization using RestCountries API
"""
import requests
from typing import List, Dict, Optional

REST_COUNTRIES_URL = "https://restcountries.com/v3.1/all"

def get_countries() -> List[Dict]:
    """Fetch all countries with official names, cca2 codes."""
    try:
        resp = requests.get(REST_COUNTRIES_URL, timeout=5)
        resp.raise_for_status()
        countries = resp.json()
        return [
            {
                "name": c.get("name", {}).get("common", ""),
                "official": c.get("name", {}).get("official", ""),
                "cca2": c.get("cca2", ""),
                "region": c.get("region", ""),
            }
            for c in countries
        ]
    except Exception:
        return []

# Static fallback for cities (replace with a real API like Geonames in production)
CITIES_DB = {
    "PK": ["Lahore", "Karachi", "Islamabad", "Rawalpindi", "Faisalabad"],
    "IN": ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai"],
    "US": ["New York", "San Francisco", "Seattle", "Austin", "Chicago"],
    "GB": ["London", "Manchester", "Birmingham", "Edinburgh"],
    "CA": ["Toronto", "Vancouver", "Montreal", "Ottawa"],
}

def get_cities_for_country(country_code: str = "US") -> List[str]:
    """Return a list of cities for a given country code (static fallback)."""
    return CITIES_DB.get(country_code.upper(), [])

def validate_and_normalize_location(raw_city: str, raw_country: str) -> Dict:
    """
    Takes raw user input like 'Lahore, Pakistan' or just 'Lahore',
    returns a structured location dict with validated country and city.
    """
    countries = get_countries()
    city = raw_city.strip()
    country_input = raw_country.strip() if raw_country else ""
    matched_country = None
    
    # Try exact match first
    for c in countries:
        if (country_input.lower() in c["name"].lower() or
            country_input.upper() == c["cca2"]):
            matched_country = c
            break
    
    # Try partial match if no exact match
    if not matched_country and country_input:
        for c in countries:
            if country_input.lower() in c["name"].lower():
                matched_country = c
                break
    
    country_code = matched_country["cca2"] if matched_country else ""
    country_name = matched_country["name"] if matched_country else country_input
    
    return {
        "city": city,
        "country": country_name,
        "country_code": country_code,
        "full_location": f"{city}, {country_name}" if city else country_name
    }
