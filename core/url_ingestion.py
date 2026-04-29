"""
URL Ingestion - Extract job postings from URLs
"""
import requests
from bs4 import BeautifulSoup

def extract_job_text_from_url(url: str) -> dict:
    """Extract job description text from a URL"""
    try:
        headers = {"User-Agent": "Mozilla/5.0 (compatible; JobSync/2.0)"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Remove unwanted elements
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        
        # Try common job description containers
        text = ""
        for sel in ["div.job-description", "div.description", "article", "main", "div.content"]:
            elem = soup.select_one(sel)
            if elem:
                text = elem.get_text(separator="\n", strip=True)
                break
        
        # Fallback to body
        if not text:
            text = soup.body.get_text(separator="\n", strip=True)[:5000] if soup.body else ""
        
        return {"raw_text": text, "url": url, "success": True}
    except Exception as e:
        return {"raw_text": "", "url": url, "success": False, "error": str(e)}
