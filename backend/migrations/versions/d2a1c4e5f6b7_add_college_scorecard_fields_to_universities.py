"""add college scorecard fields to universities

Revision ID: d2a1c4e5f6b7
Revises: m20260524_merge_heads
Create Date: 2026-05-24 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d2a1c4e5f6b7"
down_revision: Union[str, Sequence[str], None] = "c3f1b2a9d4e6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("universities", sa.Column("avg_sat", sa.Integer(), nullable=True))
    op.add_column("universities", sa.Column("avg_act", sa.Float(), nullable=True))
    op.add_column("universities", sa.Column("net_price_public", sa.Integer(), nullable=True))
    op.add_column("universities", sa.Column("net_price_private", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("universities", "net_price_private")
    op.drop_column("universities", "net_price_public")
    op.drop_column("universities", "avg_act")
    op.drop_column("universities", "avg_sat")