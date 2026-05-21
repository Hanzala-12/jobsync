"""add missing university timestamp columns

Revision ID: f2c1a9d8e4b6
Revises: d9e8f7c6b5a4
Create Date: 2026-05-21 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f2c1a9d8e4b6'
down_revision: Union[str, Sequence[str], None] = 'd9e8f7c6b5a4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'universities',
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.add_column(
        'universities',
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.add_column(
        'universities',
        sa.Column('last_scraped_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_universities_last_scraped_at'), 'universities', ['last_scraped_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_universities_last_scraped_at'), table_name='universities')
    op.drop_column('universities', 'last_scraped_at')
    op.drop_column('universities', 'updated_at')
    op.drop_column('universities', 'created_at')
