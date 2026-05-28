"""merge profile and verification heads

Revision ID: m20260526_merge_profile_heads
Revises: b1c2d3e4f5a6, f0a1b2c3d4e5
Create Date: 2026-05-26 00:00:00.000000
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m20260526_merge_profile_heads"
down_revision: Union[str, Sequence[str], None] = ("b1c2d3e4f5a6", "f0a1b2c3d4e5")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
