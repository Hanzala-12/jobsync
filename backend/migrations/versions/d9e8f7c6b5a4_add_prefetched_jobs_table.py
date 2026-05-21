"""add prefetched_jobs table

Revision ID: d9e8f7c6b5a4
Revises: a7d1c2e3f4b5
Create Date: 2026-05-21 00:00:02.000000

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd9e8f7c6b5a4'
down_revision: Union[str, Sequence[str], None] = 'a7d1c2e3f4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS prefetched_jobs (
            job_id VARCHAR NOT NULL PRIMARY KEY,
            title VARCHAR,
            company VARCHAR,
            description TEXT,
            source VARCHAR,
            fetched_at TIMESTAMP WITHOUT TIME ZONE
        )
        """
    )


def downgrade() -> None:
    op.drop_table('prefetched_jobs')