from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import tempfile
from urllib.parse import urlparse
from typing import Any, Dict

import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api").rstrip("/")
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SERVER_LOG_HANDLES = []


def _api_host_port() -> tuple[str, int]:
    parsed = urlparse(BASE_URL)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 8000
    return host, port


def _ensure_api_running() -> None:
    host, port = _api_host_port()
    log_dir = tempfile.gettempdir()
    stdout_path = os.path.join(log_dir, f"debug_student_flow_uvicorn_{port}.out.log")
    stderr_path = os.path.join(log_dir, f"debug_student_flow_uvicorn_{port}.err.log")
    try:
        requests.get(f"{BASE_URL}/health", timeout=2)
        return
    except Exception:
        pass

    creation_flags = 0
    if os.name == "nt":
        creation_flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP

    stdout_handle = open(stdout_path, "w", encoding="utf-8")
    stderr_handle = open(stderr_path, "w", encoding="utf-8")
    _SERVER_LOG_HANDLES.extend([stdout_handle, stderr_handle])

    subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "backend.main:app", "--host", host, "--port", str(port), "--log-level", "warning"],
        cwd=REPO_ROOT,
        stdout=stdout_handle,
        stderr=stderr_handle,
        creationflags=creation_flags,
    )

    deadline = time.time() + 300
    while time.time() < deadline:
        try:
            response = requests.get(f"{BASE_URL}/health", timeout=2)
            if response.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)

    stdout_handle.flush()
    stderr_handle.flush()
    raise RuntimeError(
        f"API server did not become ready in time; logs: {stdout_path}, {stderr_path}"
    )


def _pretty(title: str, payload: Any) -> None:
    print(f"\n{title}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> None:
    _ensure_api_running()
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
    print('profile status', profile_response.status_code)
    try:
        profile_response.raise_for_status()
    except Exception:
        print('profile response text:', profile_response.text)
        raise
    profile = profile_response.json()
    profile_id = profile["id"]
    _pretty("Created profile", profile)

    recommendations_response = session.post(
        f"{BASE_URL}/student/match/recommend",
        json={"student_profile_id": profile_id, "limit": 10},
        timeout=120,
    )
    print('recommend status', recommendations_response.status_code)
    print('recommend response text:', recommendations_response.text)
    try:
        recommendations_response.raise_for_status()
    except Exception:
        raise
    recommendations = recommendations_response.json().get("results", [])
    _pretty("Recommendations", recommendations[:3])


if __name__ == "__main__":
    main()
