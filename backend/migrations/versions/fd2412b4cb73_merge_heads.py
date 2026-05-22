"""merge heads

Revision ID: fd2412b4cb73
Revises: add_skill_columns, a1b2c3d4e5f6
Create Date: 2026-05-22 00:20:43.442797

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fd2412b4cb73'
down_revision: Union[str, Sequence[str], None] = ('add_skill_columns', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
