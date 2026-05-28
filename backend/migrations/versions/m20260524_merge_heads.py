"""merge heads

Revision ID: m20260524_merge_heads
Revises: 7a8b9c0d1e2f, d1e2f3a4b5c6
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'm20260524_merge_heads'
down_revision: Union[str, Sequence[str], None] = ('7a8b9c0d1e2f', 'd1e2f3a4b5c6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge multiple heads into a single linear history.
    This is a no-op merge revision; schema changes should already be present in child revisions.
    """
    pass


def downgrade() -> None:
    pass
