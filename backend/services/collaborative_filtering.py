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
