"""add selected student profile preference

Revision ID: d1e2f3a4b5c6
Revises: 6e1a2b3c4d5e
Create Date: 2026-05-23 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd1e2f3a4b5c6'
down_revision: Union[str, Sequence[str], None] = '6e1a2b3c4d5e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('user_preferences', sa.Column('selected_student_profile_id', sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column('user_preferences', 'selected_student_profile_id')