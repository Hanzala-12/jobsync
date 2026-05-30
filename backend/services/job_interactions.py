from __future__ import annotations

from sqlalchemy.orm import Session

from backend.models import UserJobInteraction


def record_user_job_interaction(db: Session, user_id: int, job_id: int, interaction_type: str) -> None:
    db.add(
        UserJobInteraction(
            user_id=user_id,
            job_id=job_id,
            interaction_type=str(interaction_type or "").strip().lower(),
        )
    )
    db.commit()
