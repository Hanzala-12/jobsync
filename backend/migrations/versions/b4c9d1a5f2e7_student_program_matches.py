"""Deprecated student program matches and academic background schema.

Revision ID: b4c9d1a5f2e7
Revises: e3b7c5d9a1f2
Create Date: 2026-05-21 00:00:00.000000

This revision is intentionally left as a no-op.
The complete study schema is created in the later linear migration chain.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4c9d1a5f2e7'
down_revision: Union[str, Sequence[str], None] = 'e3b7c5d9a1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
