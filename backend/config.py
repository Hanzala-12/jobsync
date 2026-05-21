from __future__ import annotations

import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

# Scraper settings
SCRAPER_TIMEOUT = int(os.getenv("SCRAPER_TIMEOUT", "30"))
SCRAPER_RATE_LIMIT_DELAY = float(os.getenv("SCRAPER_RATE_LIMIT_DELAY", "2"))
USER_AGENT = os.getenv("USER_AGENT", "Mozilla/5.0 (compatible; JobFinderBot/1.0)")

# Feature flags
ENABLE_JOB_SCRAPING = os.getenv("ENABLE_JOB_SCRAPING", "true").lower() in {"1", "true", "yes"}
ENABLE_UNIVERSITY_SCRAPING = os.getenv("ENABLE_UNIVERSITY_SCRAPING", "true").lower() in {"1", "true", "yes"}

# Other
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
