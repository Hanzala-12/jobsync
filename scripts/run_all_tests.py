from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run_step(label: str, script_name: str) -> int:
    script_path = ROOT / "scripts" / script_name
    print(f"\n=== {label} ===")
    result = subprocess.run([sys.executable, str(script_path)], cwd=ROOT)
    if result.returncode != 0:
        print(f"{label} failed")
    else:
        print(f"{label} passed")
    return result.returncode


def run_http_smoke_checks() -> int:
    try:
        import requests
    except Exception as exc:
        print(f"\n=== HTTP smoke checks ===\nSkipped: requests not available ({exc})")
        return 0

    base_url = "http://127.0.0.1:8000"
    print("\n=== HTTP smoke checks ===")
    try:
        health = requests.get(f"{base_url}/health", timeout=20)
        print(f"GET /health -> {health.status_code}")
        print(health.text[:500])

        jobs = requests.get(
            f"{base_url}/jobs/search",
            params={"query": "software engineer", "limit": 5},
            timeout=60,
        )
        print(f"GET /jobs/search -> {jobs.status_code}")
        print(jobs.text[:500])

        student = requests.post(
            f"{base_url}/api/student/profile",
            json={
                "gpa": 3.5,
                "gre_score": 315,
                "toefl_score": 105,
                "ielts_score": 7.5,
                "budget_per_year": 25000,
                "preferred_countries": ["Germany"],
                "intended_major": "Computer Science",
                "degree_level": "Masters",
                "academic_background": "Computer science background",
            },
            timeout=60,
        )
        print(f"POST /api/student/profile -> {student.status_code}")
        print(student.text[:500])
        return 0
    except Exception as exc:
        print(f"HTTP smoke checks failed: {exc}")
        return 1


def main() -> int:
    steps = [
        ("Supabase connection test", "test_supabase_connection.py"),
        ("Health check", "health_check.py"),
        ("CRUD round-trip", "test_crud.py"),
    ]

    for label, script_name in steps:
        code = run_step(label, script_name)
        if code != 0:
            return code

    return run_http_smoke_checks()


if __name__ == "__main__":
    raise SystemExit(main())