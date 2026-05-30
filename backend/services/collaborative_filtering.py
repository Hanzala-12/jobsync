from __future__ import annotations

import logging
import os
from typing import Optional

import numpy as np
from scipy import sparse

logger = logging.getLogger(__name__)


# Feature flag to enable collaborative filtering
ENABLE_COLLABORATIVE_FILTERING = os.getenv("ENABLE_COLLABORATIVE_FILTERING", "false").lower() in {"1", "true", "yes"}


# Model storage path
_MODEL_PATH = os.getenv("CF_MODEL_PATH", "cf_model.npz")

# In-memory cache
_cached = {
    "user_ids": None,
    "job_ids": None,
    "user_factors": None,
    "item_factors": None,
}


def _save_model(user_ids: np.ndarray, job_ids: np.ndarray, user_factors: np.ndarray, item_factors: np.ndarray) -> None:
    try:
        np.savez_compressed(_MODEL_PATH, user_ids=user_ids, job_ids=job_ids, user_factors=user_factors, item_factors=item_factors)
        logger.info("Saved CF model to %s", _MODEL_PATH)
    except Exception:
        logger.exception("Failed to save CF model")


def _load_model() -> bool:
    if _cached["user_ids"] is not None:
        return True
    if not os.path.exists(_MODEL_PATH):
        return False
    try:
        data = np.load(_MODEL_PATH, allow_pickle=True)
        _cached["user_ids"] = data["user_ids"].astype(int)
        _cached["job_ids"] = data["job_ids"].astype(int)
        _cached["user_factors"] = data["user_factors"]
        _cached["item_factors"] = data["item_factors"]
        logger.info("Loaded CF model from %s", _MODEL_PATH)
        return True
    except Exception:
        logger.exception("Failed to load CF model")
        return False


def train_collaborative_filtering_model(db) -> dict:
    """Train or retrain the collaborative filtering model from user-job interactions.

    This function prefers the `implicit` library when available; if not present it falls back
    to a simple popularity-based item factorization.
    """
    if not ENABLE_COLLABORATIVE_FILTERING:
        logger.info("Collaborative filtering disabled; skipping training")
        return {"skipped": True}

    try:
        from backend.models import UserJobInteraction
    except Exception:
        logger.exception("UserJobInteraction model not available; cannot train CF")
        return {"error": "no_model"}

    # Load interactions: (user_id, job_id, weight)
    interactions = db.query(UserJobInteraction.user_id, UserJobInteraction.job_id, UserJobInteraction.interaction_type).all()
    if not interactions:
        logger.info("No interactions found for CF training")
        return {"items": 0}

    # Interaction weights
    weights = {"view": 1.0, "save": 3.0, "apply": 5.0}

    user_ids = []
    job_ids = []
    data_vals = []
    for user_id, job_id, interaction in interactions:
        user_ids.append(int(user_id))
        job_ids.append(int(job_id))
        data_vals.append(float(weights.get(interaction, 1.0)))

    if not user_ids:
        logger.info("No weighted interactions to train on")
        return {"items": 0}

    unique_user_ids, user_index = np.unique(np.array(user_ids, dtype=int), return_inverse=True)
    unique_job_ids, job_index = np.unique(np.array(job_ids, dtype=int), return_inverse=True)

    # Build sparse item-user matrix expected by implicit: (items x users)
    mat = sparse.coo_matrix((data_vals, (job_index, user_index)), shape=(len(unique_job_ids), len(unique_user_ids))).tocsr()

    # Try to train with implicit if available
    try:
        import implicit

        # ALS on implicit requires confidence matrix; use basic ALS
        factors = int(os.getenv("CF_FACTORS", "64"))
        regularization = float(os.getenv("CF_REG", "0.01"))
        iterations = int(os.getenv("CF_ITERS", "10"))

        model = implicit.als.AlternatingLeastSquares(factors=factors, regularization=regularization, iterations=iterations)
        # implicit expects item-user as (items x users) with dtype float32
        model.fit(mat.astype('float32'))

        item_factors = model.item_factors.astype('float32')
        user_factors = model.user_factors.astype('float32')
        _save_model(unique_user_ids, unique_job_ids, user_factors, item_factors)
        # clear cache and reload
        _cached.update({"user_ids": None, "job_ids": None, "user_factors": None, "item_factors": None})
        _load_model()
        return {"trained_users": int(len(unique_user_ids)), "trained_jobs": int(len(unique_job_ids))}
    except Exception:
        logger.exception("Implicit training unavailable or failed; falling back to simple popularity model")

    # Fallback: simple SVD using randomized SVD on the sparse matrix
    try:
        from sklearn.utils.extmath import randomized_svd

        U, Sigma, VT = randomized_svd(mat, n_components=min(32, min(mat.shape) - 1))
        # create simple factors
        item_factors = U.dot(np.diag(Sigma)).astype('float32')
        user_factors = VT.T.astype('float32')
        _save_model(unique_user_ids, unique_job_ids, user_factors, item_factors)
        _cached.update({"user_ids": None, "job_ids": None, "user_factors": None, "item_factors": None})
        _load_model()
        return {"trained_users": int(len(unique_user_ids)), "trained_jobs": int(len(unique_job_ids)), "fallback": True}
    except Exception:
        logger.exception("Fallback CF training failed")
        return {"error": "training_failed"}


def get_collaborative_filtering_score(user_id: Optional[int], job_id: int) -> float:
    """Return a normalized CF score in [0, 1]. If unavailable, return 0.0."""
    if not ENABLE_COLLABORATIVE_FILTERING:
        return 0.0
    if user_id is None:
        return 0.0

    if not _load_model():
        return 0.0

    try:
        user_ids = _cached["user_ids"]
        job_ids = _cached["job_ids"]
        user_factors = _cached["user_factors"]
        item_factors = _cached["item_factors"]

        # locate indices
        u_idx = int(np.where(user_ids == int(user_id))[0][0]) if user_ids is not None else None
        j_idx = int(np.where(job_ids == int(job_id))[0][0]) if job_ids is not None else None
        if u_idx is None or j_idx is None:
            return 0.0

        uf = user_factors[u_idx]
        jf = item_factors[j_idx]
        raw = float(np.dot(uf, jf))
        # normalize to (-1,1) then map to (0,1)
        norm = raw / (1.0 + abs(raw))
        score = (norm + 1.0) / 2.0
        return max(0.0, min(1.0, score))
    except Exception:
        logger.exception("Error computing CF score for user=%s job=%s", user_id, job_id)
        return 0.0


def combined_rank_score(content_score: float, cf_score: float) -> float:
    """Combine content-based score and cf_score (0..1) into a single ranking score.

    Uses 70% weight for content and 30% for CF influence scaled to the content score magnitude.
    """
    try:
        if not cf_score:
            return float(content_score)
        scale = max(float(content_score), 1.0)
        return float(0.7 * float(content_score) + 0.3 * (float(cf_score) * scale))
    except Exception:
        logger.exception("Failed to combine scores")
        return float(content_score)
from __future__ import annotations

import json
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from backend.models import Job, UserJobInteraction

logger = logging.getLogger(__name__)

ENABLE_COLLABORATIVE_FILTERING = os.getenv("ENABLE_COLLABORATIVE_FILTERING", "false").strip().lower() in {"1", "true", "yes", "on"}
CONTENT_WEIGHT = float(os.getenv("COLLABORATIVE_FILTERING_CONTENT_WEIGHT", "0.7"))
CF_WEIGHT = float(os.getenv("COLLABORATIVE_FILTERING_CF_WEIGHT", "0.3"))
MODEL_PATH = Path(__file__).resolve().parents[2] / "data" / "collaborative_filtering_model.json"

INTERACTION_WEIGHTS = {
    "view": 1.0,
    "save": 3.0,
    "apply": 5.0,
}


def _normalize_interaction_type(value: str) -> str:
    return str(value or "").strip().lower()


def _load_model() -> dict[str, Any] | None:
    if not MODEL_PATH.exists():
        return None
    try:
        with MODEL_PATH.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, dict):
            return payload
    except Exception:
        logger.exception("Failed to load collaborative filtering model")
    return None


def load_collaborative_filtering_model() -> dict[str, Any] | None:
    return _load_model()


def train_collaborative_filtering_model(db: Session) -> dict[str, Any]:
    interactions = (
        db.query(UserJobInteraction)
        .order_by(UserJobInteraction.timestamp.asc())
        .all()
    )

    user_ids = sorted({int(item.user_id) for item in interactions})
    job_ids = sorted({int(item.job_id) for item in interactions})
    user_index = {user_id: index for index, user_id in enumerate(user_ids)}
    job_index = {job_id: index for index, job_id in enumerate(job_ids)}

    user_vectors: dict[int, dict[int, float]] = defaultdict(lambda: defaultdict(float))
    item_popularity: dict[int, float] = defaultdict(float)

    for item in interactions:
        interaction_type = _normalize_interaction_type(item.interaction_type)
        weight = INTERACTION_WEIGHTS.get(interaction_type, 0.0)
        if weight <= 0:
            continue
        user_vectors[int(item.user_id)][int(item.job_id)] += weight
        item_popularity[int(item.job_id)] += weight

    item_max = max(item_popularity.values(), default=1.0)

    model = {
        "model_type": "popularity",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_index": user_index,
        "job_index": job_index,
        "item_popularity": {str(job_id): float(score) for job_id, score in item_popularity.items()},
        "item_popularity_max": float(item_max),
        "user_vectors": {str(user_id): {str(job_id): float(score) for job_id, score in vector.items()} for user_id, vector in user_vectors.items()},
    }

    try:
        from implicit.als import AlternatingLeastSquares  # type: ignore
        from scipy.sparse import csr_matrix  # type: ignore
        import numpy as np  # type: ignore

        if interactions and user_ids and job_ids:
            matrix = np.zeros((len(user_ids), len(job_ids)), dtype=float)
            for item in interactions:
                interaction_type = _normalize_interaction_type(item.interaction_type)
                weight = INTERACTION_WEIGHTS.get(interaction_type, 0.0)
                if weight <= 0:
                    continue
                matrix[user_index[int(item.user_id)], job_index[int(item.job_id)]] += weight

            sparse_matrix = csr_matrix(matrix)
            if sparse_matrix.nnz > 0:
                als = AlternatingLeastSquares(factors=32, regularization=0.05, iterations=12)
                als.fit(sparse_matrix)
                model.update(
                    {
                        "model_type": "als",
                        "user_factors": als.user_factors.tolist(),
                        "item_factors": als.item_factors.tolist(),
                    }
                )
    except Exception:
        logger.info("implicit ALS unavailable; storing popularity-only collaborative filtering model", exc_info=True)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_PATH.open("w", encoding="utf-8") as handle:
        json.dump(model, handle)
    return model


def get_collaborative_filtering_score(user_id: int | None, job_id: int | None) -> float:
    if not ENABLE_COLLABORATIVE_FILTERING or not user_id or not job_id:
        return 0.0

    model = _load_model()
    if not model:
        return 0.0

    try:
        model_type = str(model.get("model_type") or "popularity")
        if model_type == "als":
            user_index = model.get("user_index") or {}
            job_index = model.get("job_index") or {}
            user_pos = user_index.get(str(user_id)) if isinstance(user_index, dict) else user_index.get(user_id)
            job_pos = job_index.get(str(job_id)) if isinstance(job_index, dict) else job_index.get(job_id)
            if user_pos is None or job_pos is None:
                return 0.0
            user_factors = model.get("user_factors") or []
            item_factors = model.get("item_factors") or []
            if user_pos >= len(user_factors) or job_pos >= len(item_factors):
                return 0.0
            user_vec = user_factors[user_pos]
            item_vec = item_factors[job_pos]
            return float(sum(float(u) * float(i) for u, i in zip(user_vec, item_vec)))

        item_popularity = model.get("item_popularity") or {}
        item_max = float(model.get("item_popularity_max") or 1.0)
        raw = item_popularity.get(str(job_id)) if isinstance(item_popularity, dict) else None
        if raw is None:
            raw = item_popularity.get(job_id, 0.0) if isinstance(item_popularity, dict) else 0.0
        return float(raw) / item_max if item_max > 0 else float(raw)
    except Exception:
        logger.exception("Failed to score collaborative filtering candidate")
        return 0.0


def combined_rank_score(content_score: float, cf_score: float) -> float:
    content_norm = max(0.0, float(content_score)) / 100.0
    cf_norm = max(0.0, float(cf_score))
    return CONTENT_WEIGHT * content_norm + CF_WEIGHT * cf_norm
