from __future__ import annotations

import logging
from typing import Any, Dict, Optional

try:
    from celery import shared_task
except Exception:  # pragma: no cover - optional dependency in lightweight dev envs
    def shared_task(name=None, bind=False):
        def _decorator(func):
            return func

        return _decorator

from backend.celery_app import celery_enabled
from backend.monitoring import record_celery_task
from backend.tasks.state import new_task_id, record_task_state


_logger = logging.getLogger(__name__)
_TASK_NAME = "backend.tasks.cover_letter_tasks.generate_cover_letter_artifacts"


def generate_cover_letter_artifacts(
    job_id: Optional[int],
    resume_text: str,
    company: Optional[str],
    role: Optional[str],
    job_description: str,
    source: Optional[str],
    job_url: Optional[str],
) -> Dict[str, Any]:
    from core.rag_service import generate_cover_letter_with_rag, save_cover_letter_artifacts

    draft, source_ids, retrieved_chunks = generate_cover_letter_with_rag(
        job_description,
        resume_text,
        company_name=company,
        role=role,
        tone="professional",
        top_k=5,
        metadata_filter={"company": company} if company else None,
    )
    save_cover_letter_artifacts(
        job_id,
        draft,
        source_ids,
        retrieved_chunks,
        metadata={
            "company": company,
            "role": role,
            "source": source,
            "job_url": job_url,
        },
    )
    return {
        "job_id": job_id,
        "draft": draft,
        "source_ids": source_ids,
        "retrieved_chunks": retrieved_chunks,
        "saved": True,
    }


@shared_task(name=_TASK_NAME, bind=True)
def generate_cover_letter_artifacts_task(
    self,
    job_id: Optional[int],
    resume_text: str,
    company: Optional[str],
    role: Optional[str],
    job_description: str,
    source: Optional[str],
    job_url: Optional[str],
) -> Dict[str, Any]:
    try:
        result = generate_cover_letter_artifacts(job_id, resume_text, company, role, job_description, source, job_url)
        record_celery_task(_TASK_NAME, "completed")
        return result
    except Exception:
        record_celery_task(_TASK_NAME, "failed")
        raise


def dispatch_cover_letter_generation(
    job_id: Optional[int],
    resume_text: str,
    company: Optional[str],
    role: Optional[str],
    job_description: str,
    source: Optional[str],
    job_url: Optional[str],
) -> Dict[str, Any]:
    task_id = new_task_id()
    task_kwargs = {
        "job_id": job_id,
        "resume_text": resume_text,
        "company": company,
        "role": role,
        "job_description": job_description,
        "source": source,
        "job_url": job_url,
    }
    record_task_state(task_id, "pending", task_name=_TASK_NAME, result={"job_id": job_id})

    if celery_enabled():
        try:
            async_result = generate_cover_letter_artifacts_task.apply_async(kwargs=task_kwargs, task_id=task_id)
            return {"task_id": async_result.id, "status": "pending", "mode": "celery"}
        except Exception as exc:
            _logger.warning("Celery enqueue failed for cover letter generation; running locally instead: %s", exc)

    try:
        record_task_state(task_id, "running", task_name=_TASK_NAME, result={"job_id": job_id})
        result = generate_cover_letter_artifacts(**task_kwargs)
        record_task_state(task_id, "completed", task_name=_TASK_NAME, result=result)
        record_celery_task(_TASK_NAME, "completed")
        return {"task_id": task_id, "status": "completed", "mode": "sync", "result": result}
    except Exception as exc:
        record_task_state(task_id, "failed", task_name=_TASK_NAME, error=str(exc))
        record_celery_task(_TASK_NAME, "failed")
        raise
