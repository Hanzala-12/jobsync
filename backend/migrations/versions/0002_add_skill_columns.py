"""Add job_skills and profile_skills columns

Revision ID: add_skill_columns
Revises: 
Create Date: 2026-05-21 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_skill_columns'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_skills JSON DEFAULT '[]'")
    op.execute("ALTER TABLE student_profiles ADD COLUMN IF NOT EXISTS profile_skills JSON DEFAULT '[]'")


def downgrade():
    op.execute("ALTER TABLE jobs DROP COLUMN IF EXISTS job_skills")
    op.execute("ALTER TABLE student_profiles DROP COLUMN IF EXISTS profile_skills")
