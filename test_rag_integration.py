"""Minimal integration test for RAG-enhanced cover letter generation."""

from __future__ import annotations

import json
from pathlib import Path

from core.rag_service import generate_cover_letter_with_rag


def load_sample_job() -> dict:
    sample_path = Path("samples") / "sample_rag_job.json"
    if sample_path.exists():
        return json.loads(sample_path.read_text(encoding="utf-8"))

    return {
        "job_description": "We are hiring a Python backend engineer in Karachi with REST API, PostgreSQL, and AWS experience.",
        "company": "Sample Company",
        "role": "Backend Engineer",
        "resume_summary": "Backend engineer with Python, PostgreSQL, REST API, and AWS experience.",
    }


def main() -> None:
    job = load_sample_job()
    cover_letter, source_ids, _ = generate_cover_letter_with_rag(
        job.get("job_description", ""),
        job.get("resume_summary", "Backend engineer with Python, SQL, and AWS experience."),
        company_name=job.get("company", ""),
        role=job.get("role", ""),
        tone="professional",
        top_k=5,
    )

    print("=== Cover Letter ===")
    print(cover_letter)
    print("\n=== Source IDs ===")
    print(source_ids)


if __name__ == "__main__":
    main()
