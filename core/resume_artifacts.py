from __future__ import annotations

import json
import os
from typing import Any, Mapping, Sequence


DEFAULT_RESUME_OUTPUT_DIR = os.path.join(os.getcwd(), "outputs", "resumes")


def _ensure_output_dir(output_dir: str) -> str:
    os.makedirs(output_dir, exist_ok=True)
    return output_dir


def save_resume_artifacts(
    job_id: int | None,
    original_resume: str,
    fixed_resume_text: str,
    html_resume: str,
    changes_made: Sequence[str],
    *,
    output_dir: str = DEFAULT_RESUME_OUTPUT_DIR,
    file_prefix: str = "tailored_resume",
    metadata: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    _ensure_output_dir(output_dir)

    suffix = str(job_id) if job_id is not None else "unscoped"
    txt_path = os.path.join(output_dir, f"{file_prefix}_{suffix}.txt")
    html_path = os.path.join(output_dir, f"{file_prefix}_{suffix}.html")
    json_path = os.path.join(output_dir, f"{file_prefix}_{suffix}.json")

    with open(txt_path, "w", encoding="utf-8") as handle:
        handle.write(fixed_resume_text or "")

    with open(html_path, "w", encoding="utf-8") as handle:
        handle.write(html_resume or "")

    payload: dict[str, Any] = {
        "job_id": job_id,
        "original_resume": original_resume,
        "fixed_resume_text": fixed_resume_text,
        "changes_made": list(changes_made),
    }
    if metadata:
        payload.update(dict(metadata))

    with open(json_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    return {"text_path": txt_path, "html_path": html_path, "json_path": json_path}
