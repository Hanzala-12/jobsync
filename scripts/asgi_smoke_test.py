"""Lightweight ASGI smoke tests that run against the app object (no Uvicorn required).

This script attempts to exercise a few key endpoints using an ASGI client.
It overrides the `require_current_user` dependency to avoid needing an auth token.
"""
from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

# ensure repo root is importable
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

try:
    import httpx
    from httpx import ASGITransport
except Exception:
    httpx = None

import importlib

import backend.main as m
import backend.security as security

os.environ.setdefault("TESTING_MODE", "true")
os.environ.setdefault("TEST_USER_EMAIL", "dev@example.com")


def override_auth():
    fake_user = SimpleNamespace(id=1, email="dev@example.com")
    m.app.dependency_overrides[security.require_current_user] = lambda: fake_user


def make_client():
    override_auth()
    # Prefer TestClient for wide compatibility
    try:
        from starlette.testclient import TestClient

        client = TestClient(m.app)
        return client, "testclient"
    except Exception:
        pass

    if httpx:
        try:
            transport = ASGITransport(app=m.app)
            client = httpx.Client(transport=transport, base_url="http://test")
            return client, "httpx-asgi"
        except Exception:
            pass

    # No client available
    try:
        from starlette.testclient import TestClient

        client = TestClient(m.app)
        return client, "testclient"
    except Exception as exc:
        print("No ASGI client available:", exc)
        sys.exit(2)


def start_uvicorn_background(port: int = 8008):
    import threading
    import time

    try:
        import uvicorn
    except Exception:
        print("uvicorn not available for background server")
        return None

    def run():
        uvicorn.run(m.app, host="127.0.0.1", port=port, log_level="warning")

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    # give server a moment to start
    time.sleep(1.0)
    return thread


def run_tests():
    client, kind = make_client()
    print(f"Using client: {kind}")

    tests = []

    tests.append(("GET", "/health", None))
    tests.append(("GET", "/api/student/profile", None))
    tests.append(("GET", "/student/profile", None))

    payload = {"student_profile_id": int(8), "limit": 5}
    tests.append(("POST", "/api/student/match/recommend", payload))

    results = []
    for method, path, body in tests:
        try:
            if method == "GET":
                resp = client.get(path)
            else:
                resp = client.post(path, json=body)
            text = resp.text
            short = text[:800]
            results.append({"method": method, "path": path, "status": resp.status_code, "body_snippet": short})
            print(json.dumps(results[-1], ensure_ascii=False, indent=2))
        except Exception as exc:
            errstr = str(exc)
            results.append({"method": method, "path": path, "error": errstr})
            print(json.dumps(results[-1], ensure_ascii=False, indent=2))
            # If ASGITransport is incompatible, try starting a background uvicorn server
            if "ASGITransport" in errstr or "handle_request" in errstr:
                print("ASGI transport incompatible; trying HTTP fallback to existing server on port 8000")
                import requests
                base_candidates = ["http://127.0.0.1:8000", "http://127.0.0.1:8008"]
                worked = False
                for base in base_candidates:
                    try:
                        if method == "GET":
                            r = requests.get(base + path, timeout=10)
                        else:
                            r = requests.post(base + path, json=body, timeout=30)
                        results.append({"method": method, "path": path, "status": r.status_code, "body_snippet": r.text[:800], "base": base})
                        print(json.dumps(results[-1], ensure_ascii=False, indent=2))
                        worked = True
                        break
                    except Exception as exc2:
                        results.append({"method": method, "path": path, "error": str(exc2), "base": base})
                        print(json.dumps(results[-1], ensure_ascii=False, indent=2))
                if not worked:
                    print("HTTP fallback failed for all candidate ports")

    # cleanup
    try:
        client.close()
    except Exception:
        pass


if __name__ == "__main__":
    run_tests()
