from __future__ import annotations

import json
import os
from typing import Any, Dict

import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api").rstrip("/")


def _pretty(title: str, payload: Any) -> None:
    print(f"\n{title}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    session = requests.Session()

    profile_payload: Dict[str, Any] = {
        "gpa": 3.7,
        "gre_score": 320,
        "toefl_score": 105,
        "ielts_score": 7.5,
        "budget_per_year": 25000,
        "preferred_countries": ["Malaysia", "Singapore", "Germany"],
        "intended_major": "Computer Science",
        "degree_level": "Masters",
        "academic_background": "BSc in Software Engineering",
    }

    profile_response = session.post(f"{BASE_URL}/student/profile", json=profile_payload, timeout=60)
    profile_response.raise_for_status()
    profile = profile_response.json()
    profile_id = profile["id"]
    _pretty("Created profile", profile)

    recommendations_response = session.post(
        f"{BASE_URL}/student/match/recommend",
        json={"student_profile_id": profile_id, "limit": 10},
        timeout=120,
    )
    recommendations_response.raise_for_status()
    recommendations = recommendations_response.json().get("results", [])
    _pretty("Recommendations", recommendations[:3])

    if not recommendations:
        print("No recommendations returned")
        return

    top_match = recommendations[0]
    program_id = top_match["program"]["id"]

    detail_response = session.get(
        f"{BASE_URL}/student/match/program/{program_id}",
        params={"student_profile_id": profile_id},
        timeout=120,
    )
    detail_response.raise_for_status()
    detail = detail_response.json()
    _pretty("Top match detail", detail)

    save_response = session.post(
        f"{BASE_URL}/student/save",
        json={"student_id": profile_id, "program_id": program_id},
        timeout=60,
    )
    save_response.raise_for_status()
    _pretty("Save result", save_response.json())

    print("\nStudent flow test completed successfully.")


if __name__ == "__main__":
    main()
