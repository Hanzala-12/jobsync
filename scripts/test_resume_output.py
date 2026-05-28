#!/usr/bin/env python3
"""
Test script for resume generation output.
Usage:
  Set environment variables or edit defaults below and run:
    python scripts/test_resume_output.py

Checks:
 - Calls /auth/login to get access token
 - Calls /build_resume/{job_id}
 - Validates output for skills formatting, no placeholders, no duplicate blocks, and bullets per experience
"""
import os
import sys
import re
import requests

API_BASE = os.environ.get("API_BASE", "http://127.0.0.1:8000")
EMAIL = os.environ.get("TEST_EMAIL", "autotest+e2e2026@example.com")
PASSWORD = os.environ.get("TEST_PASSWORD", "TestPass123!")
JOB_ID_ENV = os.environ.get("JOB_ID", "").strip()

PLACEHOLDER_PATTERNS = [r"add your", r"not specified", r"experience at", r"add degree", r"your degree"]


def login(email, password):
    url = f"{API_BASE}/auth/login"
    resp = requests.post(url, json={"email": email, "password": password})
    resp.raise_for_status()
    return resp.json().get("access_token")


def call_build_resume(job_id, token):
    url = f"{API_BASE}/build_resume/{job_id}"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    if os.environ.get("FORCE_REBUILD", "").strip().lower() in {"1", "true", "yes"}:
        headers["X-Force-Rebuild"] = "1"
    resp = requests.post(url, headers=headers)
    resp.raise_for_status()
    return resp.json()


def discover_job_id(token):
    if JOB_ID_ENV:
        try:
            return int(JOB_ID_ENV)
        except Exception:
            pass
    url = f"{API_BASE}/jobs/search"
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    params = {"query": "software engineer", "location": "Pakistan", "limit": 1}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    if isinstance(data, list) and data:
        return int(data[0].get("id") or 1)
    if isinstance(data, dict):
        items = data.get("items") or []
        if items:
            return int(items[0].get("id") or 1)
    return 1


def contains_placeholder(text):
    low = (text or "").lower()
    for p in PLACEHOLDER_PATTERNS:
        if re.search(p, low):
            return True
    return False


def has_duplicate_paragraphs(text):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    seen = set()
    for p in paras:
        key = re.sub(r"\s+", " ", p).strip().lower()
        if key in seen:
            return True
        seen.add(key)
    return False


if __name__ == "__main__":
    print(f"Testing resume generation against {API_BASE}")
    try:
        token = login(EMAIL, PASSWORD)
    except Exception as e:
        print("Login failed:", e)
        sys.exit(2)

    try:
        job_id = discover_job_id(token)
    except Exception as e:
        print("Job discovery failed:", e)
        sys.exit(2)

    print(f"Using job_id={job_id}")

    try:
        out = call_build_resume(job_id, token)
    except Exception as e:
        print("build_resume API call failed:", e)
        sys.exit(2)

    fixed = out.get("fixed_resume_text") or out.get("simple_text_version") or ""
    sections = out.get("sections") or {}

    failures = []

    # 1. At least 3 skills separated by commas
    skills = sections.get("skills") or []
    skills_line = ", ".join(skills) if isinstance(skills, list) else str(skills)
    if skills_line.count(",") < 2:
        failures.append("Skills formatting: expected at least 3 skills separated by commas.")

    # 2. No placeholder phrases
    if contains_placeholder(fixed):
        failures.append("Placeholder phrases found in resume output.")

    # 3. No duplicated paragraphs
    if has_duplicate_paragraphs(fixed):
        failures.append("Duplicate paragraphs detected in output.")

    # 4. At least one bullet per work experience (if experience exists)
    experience = sections.get("experience") or []
    if experience:
        for idx, item in enumerate(experience):
            bullets = item.get("bullets") if isinstance(item, dict) else []
            if not bullets:
                failures.append(f"Experience item #{idx+1} has no bullets.")

    print("-- Resume output sample --")
    print(fixed[:4000])
    print("-- End sample --")

    if failures:
        print("FAIL:\n" + "\n".join(failures))
        sys.exit(1)

    print("PASS: Resume output checks passed.")
    sys.exit(0)
