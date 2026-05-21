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

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api").rstrip("/")
STUDENT_PROFILE_ID = int(os.getenv("STUDENT_PROFILE_ID", "8"))
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
    stdout_path = os.path.join(log_dir, f"minimal_api_test_uvicorn_{port}.out.log")
    stderr_path = os.path.join(log_dir, f"minimal_api_test_uvicorn_{port}.err.log")
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


def main() -> None:
    _ensure_api_running()
    payload: Dict[str, Any] = {"student_profile_id": STUDENT_PROFILE_ID, "limit": 10}
    try:
        response = requests.post(f"{BASE_URL}/student/match/recommend", json=payload, timeout=120)
        print(f"status={response.status_code}")
        print(response.text)
        response.raise_for_status()
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
    except Exception as exc:
        print(f"error={exc}")
        raise


if __name__ == "__main__":
    main()
