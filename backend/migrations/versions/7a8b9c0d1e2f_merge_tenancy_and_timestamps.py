"""merge tenancy and timestamp heads

Revision ID: 7a8b9c0d1e2f
Revises: 6e1a2b3c4d5e, e4f5a6b7c8d9
Create Date: 2026-05-22 18:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7a8b9c0d1e2f'
down_revision: Union[str, Sequence[str], None] = ('6e1a2b3c4d5e', 'e4f5a6b7c8d9')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
