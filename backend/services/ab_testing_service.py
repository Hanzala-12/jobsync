from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import Any, Dict, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import ABTest, ABTestAssignment, ABTestEvent


def _env_flag(name: str, default: bool = False) -> bool:
	raw = (os.getenv(name) or "").strip().lower()
	if not raw:
		return default
	return raw in {"1", "true", "yes", "on"}


ENABLE_AB_TESTING = _env_flag("ENABLE_AB_TESTING", False)

FEATURE_MATCHING = "matching_algorithm"
FEATURE_EMBEDDINGS = "embedding_model"
FEATURE_RETRIEVAL = "retrieval_strategy"


@dataclass(frozen=True)
class ABContext:
	feature_key: str
	variant: str
	algorithm_version: str
	test_id: int
	assignment_id: int


DEFAULT_TESTS = (
	{
		"name": "University Matching Algorithm",
		"feature_key": FEATURE_MATCHING,
		"description": "Compares baseline and improved student-program matching logic.",
		"control_algorithm_version": "matching_v1",
		"treatment_algorithm_version": "matching_v2",
	},
	{
		"name": "Embedding Model",
		"feature_key": FEATURE_EMBEDDINGS,
		"description": "Compares baseline embeddings versus fine-tuned embeddings.",
		"control_algorithm_version": "embeddings_baseline",
		"treatment_algorithm_version": "embeddings_finetuned",
	},
	{
		"name": "Retrieval Strategy",
		"feature_key": FEATURE_RETRIEVAL,
		"description": "Compares vector-only retrieval and hybrid retrieval.",
		"control_algorithm_version": "retrieval_vector",
		"treatment_algorithm_version": "retrieval_hybrid",
	},
)


def is_enabled() -> bool:
	return ENABLE_AB_TESTING


def ensure_default_tests(db: Session) -> None:
	if not is_enabled():
		return
	for item in DEFAULT_TESTS:
		row = db.query(ABTest).filter(ABTest.feature_key == item["feature_key"]).first()
		if row is None:
			row = ABTest(
				name=item["name"],
				feature_key=item["feature_key"],
				description=item["description"],
				is_active=True,
				traffic_split={"control": 0.5, "treatment": 0.5},
				control_algorithm_version=item["control_algorithm_version"],
				treatment_algorithm_version=item["treatment_algorithm_version"],
			)
			db.add(row)
	db.commit()


def _weighted_variant(traffic_split: Dict[str, Any]) -> str:
	control = float(traffic_split.get("control", 0.5) or 0.5)
	treatment = float(traffic_split.get("treatment", 0.5) or 0.5)
	total = control + treatment
	if total <= 0:
		return "control"
	return "control" if random.random() < (control / total) else "treatment"


def get_or_assign_context(db: Session, user_id: int, feature_key: str) -> Optional[ABContext]:
	if not is_enabled() or not user_id:
		return None

	test = db.query(ABTest).filter(ABTest.feature_key == feature_key, ABTest.is_active.is_(True)).first()
	if test is None:
		return None

	assignment = (
		db.query(ABTestAssignment)
		.filter(ABTestAssignment.ab_test_id == test.id, ABTestAssignment.user_id == user_id)
		.first()
	)
	if assignment is None:
		assignment = ABTestAssignment(
			ab_test_id=test.id,
			user_id=user_id,
			variant=_weighted_variant(dict(test.traffic_split or {})),
		)
		db.add(assignment)
		db.commit()
		db.refresh(assignment)
	else:
		assignment.last_seen_at = func.now()
		db.commit()

	algorithm_version = test.control_algorithm_version if assignment.variant == "control" else test.treatment_algorithm_version
	return ABContext(
		feature_key=feature_key,
		variant=assignment.variant,
		algorithm_version=algorithm_version,
		test_id=int(test.id),
		assignment_id=int(assignment.id),
	)


def assign_user_for_all_features(db: Session, user_id: int) -> Dict[str, ABContext]:
	contexts: Dict[str, ABContext] = {}
	if not is_enabled() or not user_id:
		return contexts
	ensure_default_tests(db)
	for item in DEFAULT_TESTS:
		context = get_or_assign_context(db, user_id, item["feature_key"])
		if context is not None:
			contexts[context.feature_key] = context
	return contexts


def log_event(
	db: Session,
	*,
	user_id: int,
	feature_key: str,
	event_type: str,
	match_score: Optional[float] = None,
	program_id: Optional[int] = None,
	job_id: Optional[int] = None,
	user_clicks: Optional[Dict[str, Any]] = None,
	event_metadata: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
	if not is_enabled() or not user_id:
		return None

	context = get_or_assign_context(db, user_id, feature_key)
	if context is None:
		return None

	row = ABTestEvent(
		ab_test_id=context.test_id,
		assignment_id=context.assignment_id,
		user_id=user_id,
		job_id=job_id,
		program_id=program_id,
		match_score=match_score,
		algorithm_version=context.algorithm_version,
		event_type=event_type,
		user_clicks=dict(user_clicks or {}),
		event_metadata=dict(event_metadata or {}),
	)
	db.add(row)
	db.commit()
	db.refresh(row)
	return int(row.id)
