"""add indexes and job timestamps for monitoring

Revision ID: m20260527_monitoring_indexes
Revises: m20260527_program_field_provenance
Create Date: 2026-05-27 00:30:00.000001

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m20260527_monitoring_indexes"
down_revision: Union[str, Sequence[str], None] = "m20260527_program_field_provenance"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add started_at and completed_at to program_scrape_jobs
    op.add_column("program_scrape_jobs", sa.Column("started_at", sa.DateTime(), nullable=True))
    op.add_column("program_scrape_jobs", sa.Column("completed_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_program_scrape_jobs_retry_count"), "program_scrape_jobs", ["retry_count"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_program_scrape_jobs_retry_count"), table_name="program_scrape_jobs")
    op.drop_column("program_scrape_jobs", "completed_at")
    op.drop_column("program_scrape_jobs", "started_at")