"""Add job_skills and profile_skills columns

Revision ID: add_skill_columns
Revises: 
Create Date: 2026-05-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = 'add_skill_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "job_skills" not in {col["name"] for col in inspector.get_columns("jobs")}:
        op.add_column("jobs", sa.Column("job_skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))
    if "profile_skills" not in {col["name"] for col in inspector.get_columns("student_profiles")}:
        op.add_column("student_profiles", sa.Column("profile_skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    if "job_skills" in {col["name"] for col in inspector.get_columns("jobs")}:
        op.drop_column("jobs", "job_skills")
    if "profile_skills" in {col["name"] for col in inspector.get_columns("student_profiles")}:
        op.drop_column("student_profiles", "profile_skills")
