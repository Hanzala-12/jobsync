"""Deprecated university recommender enrichment schema.

Revision ID: e3b7c5d9a1f2
Revises: 9f8a1c2d3e4f
Create Date: 2026-05-21 00:00:00.000000

This revision is intentionally left as a no-op.
The study/university schema is created in a later linear migration so fresh
databases do not fail on missing tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e3b7c5d9a1f2'
down_revision: Union[str, Sequence[str], None] = '9f8a1c2d3e4f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass