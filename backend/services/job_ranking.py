from __future__ import annotations

import logging
import os
from typing import Iterable, List

from backend.services.collaborative_filtering import ENABLE_COLLABORATIVE_FILTERING, combined_rank_score, get_collaborative_filtering_score

logger = logging.getLogger(__name__)

ENABLE_CROSS_ENCODER = os.getenv("ENABLE_CROSS_ENCODER", "false").lower() in {"1", "true", "yes"}
_CROSS_ENCODER = None
_CROSS_ENCODER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


def _build_ranking_query(query: str, profile: object | None = None) -> str:
    pieces = [str(query or "").strip()]
    if profile is not None:
        for attr in ("preferred_job_titles", "skills", "intended_major", "academic_background", "preferred_work_location"):
            value = getattr(profile, attr, None)
            if value:
                if isinstance(value, (list, tuple, set)):
                    parts = [str(item) for item in value if str(item).strip()]
                else:
                    parts = [str(value).strip()]
                pieces.extend([part for part in parts if part])
    return " ".join(piece for piece in pieces if piece)


def _load_cross_encoder():
    global _CROSS_ENCODER
    if _CROSS_ENCODER is not None:
        return _CROSS_ENCODER

    if not ENABLE_CROSS_ENCODER:
        return None

    try:
        from sentence_transformers import CrossEncoder

        _CROSS_ENCODER = CrossEncoder(_CROSS_ENCODER_MODEL)
        logger.info("Loaded cross-encoder model %s", _CROSS_ENCODER_MODEL)
        return _CROSS_ENCODER
    except Exception:
        logger.exception("Failed to load cross-encoder model %s; falling back to baseline ranking", _CROSS_ENCODER_MODEL)
        _CROSS_ENCODER = False
        return None


def rerank_job_candidates(
    query: str,
    jobs: Iterable[object],
    profile: object | None = None,
    *,
    user_id: int | None = None,
    content_scores: dict[int, float] | None = None,
) -> List[object]:
    jobs = list(jobs)
    if not ENABLE_CROSS_ENCODER or not jobs:
        if not ENABLE_COLLABORATIVE_FILTERING:
            return jobs

        scored_jobs = []
        for job in jobs:
            job_id = int(getattr(job, "id", 0) or 0)
            content_score = float((content_scores or {}).get(job_id, 0.0))
            cf_score = get_collaborative_filtering_score(user_id, job_id)
            scored_jobs.append((combined_rank_score(content_score, cf_score), job))
        scored_jobs.sort(key=lambda item: (item[0], int(getattr(item[1], "id", 0) or 0)), reverse=True)
        return [job for _, job in scored_jobs]

    model = _load_cross_encoder()
    if model is None:
        return jobs

    ranking_query = _build_ranking_query(query, profile)
    pairs = [
        (
            ranking_query,
            " ".join(
                filter(
                    None,
                    [
                        str(getattr(job, "title", "") or ""),
                        str(getattr(job, "company", "") or ""),
                        str(getattr(job, "description", "") or ""),
                    ],
                )
            ),
        )
        for job in jobs
    ]

    try:
        scores = model.predict([[query, doc] for query, doc in pairs])
        reranked = sorted(
            zip(jobs, [float(score) for score in scores]),
            key=lambda item: item[1],
            reverse=True,
        )
        return [job for job, _ in reranked]
    except Exception:
        logger.exception("Cross-encoder reranking failed; falling back to baseline ranking")
        return jobs
