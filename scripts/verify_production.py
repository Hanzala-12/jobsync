from __future__ import annotations

import argparse
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import httpx
from sqlalchemy import inspect, text

from backend.database import engine


REQUIRED_ENV_VARS = ["DATABASE_URL"]
REQUIRED_ENV_GROUPS = {
    "LLM API key": [
        "OPENROUTER_API_KEY",
        "OPENROUTER_API_KEY_2",
        "OPENAI_API_KEY",
        "OPENAI_API_KEY_2",
        "NOVITA_API_KEY",
        "NOVITA_API_KEY_2",
        "GROQ_API_KEY",
        "GROQ_API_KEY_2",
    ]
}


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str


def _normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/") or "http://127.0.0.1:8000"


def _format_table(rows: Iterable[CheckResult]) -> str:
    rows = list(rows)
    headers = ["Check", "Status", "Detail"]
    table_rows = [[result.name, "PASS" if result.passed else "FAIL", result.detail] for result in rows]

    widths = [len(headers[0]), len(headers[1]), len(headers[2])]
    for row in table_rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(str(cell)))

    def render_row(values: list[str]) -> str:
        return "| " + " | ".join(str(value).ljust(widths[index]) for index, value in enumerate(values)) + " |"

    separator = "|-" + "-| -".join("-" * width for width in widths) + "-|"
    lines = [render_row(headers), separator]
    lines.extend(render_row(row) for row in table_rows)
    return "\n".join(lines)


def _check_required_env_vars() -> CheckResult:
    missing = [name for name in REQUIRED_ENV_VARS if not os.getenv(name, "").strip()]
    if missing:
        return CheckResult(
            name="Environment variables",
            passed=False,
            detail=f"Missing: {', '.join(missing)}",
        )

    missing_groups = []
    for group_name, candidates in REQUIRED_ENV_GROUPS.items():
        if not any(os.getenv(name, "").strip() for name in candidates):
            missing_groups.append(f"{group_name} ({', '.join(candidates)})")

    if missing_groups:
        return CheckResult(
            name="Environment variables",
            passed=False,
            detail=f"Missing: {', '.join(missing_groups)}",
        )

    return CheckResult(
        name="Environment variables",
        passed=True,
        detail="Set: DATABASE_URL and at least one LLM API key",
    )


def _check_database() -> CheckResult:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected_tables = {
            "jobs",
            "universities",
            "programs",
            "student_profiles",
            "student_program_matches",
            "university_match_cache",
        }
        missing_tables = sorted(expected_tables - tables)
        if missing_tables:
            return CheckResult(
                name="Database connectivity",
                passed=False,
                detail=f"Connected, but missing tables: {', '.join(missing_tables)}",
            )
        return CheckResult(name="Database connectivity", passed=True, detail="SELECT 1 succeeded; required tables present")
    except Exception as exc:
        return CheckResult(name="Database connectivity", passed=False, detail=str(exc))


def _check_http_endpoint(client: httpx.Client, name: str, path: str) -> CheckResult:
    try:
        response = client.get(path)
        if response.status_code != 200:
            return CheckResult(name=name, passed=False, detail=f"HTTP {response.status_code}")
        return CheckResult(name=name, passed=True, detail="HTTP 200")
    except Exception as exc:
        return CheckResult(name=name, passed=False, detail=str(exc))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Production smoke test for Job Finder")
    parser.add_argument(
        "--base-url",
        default=os.getenv("BASE_URL", "http://127.0.0.1:8000"),
        help="Base URL of the deployed API, e.g. https://your-domain.com",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("VERIFY_TIMEOUT_SECONDS", "15")),
        help="HTTP timeout in seconds",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_url = _normalize_base_url(args.base_url)
    results = [
        _check_required_env_vars(),
        _check_database(),
    ]

    timeout = httpx.Timeout(args.timeout)
    with httpx.Client(base_url=base_url, timeout=timeout, follow_redirects=True) as client:
        results.append(_check_http_endpoint(client, "GET /health", "/health"))
        results.append(_check_http_endpoint(client, "GET /api/student/universities/filter", "/api/student/universities/filter?page=1&limit=1"))
        results.append(_check_http_endpoint(client, "GET /jobs/search", "/jobs/search?page=1&limit=1"))

    all_passed = all(result.passed for result in results)

    print("Production smoke test summary")
    print(_format_table(results))
    print()
    print(f"Overall result: {'PASS' if all_passed else 'FAIL'}")

    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
