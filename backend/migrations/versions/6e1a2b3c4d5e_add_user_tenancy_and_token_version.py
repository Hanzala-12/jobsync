"""add user tenancy and token version

Revision ID: 6e1a2b3c4d5e
Revises: fd2412b4cb73
Create Date: 2026-05-22 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e1a2b3c4d5e'
down_revision: Union[str, Sequence[str], None] = 'fd2412b4cb73'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SYSTEM_EMAIL = 'system@jobsync.local'


def _ensure_system_user(bind) -> int:
    bind.execute(
        sa.text(
            """
            INSERT INTO users (email, hashed_password, is_active, token_version, created_at)
            SELECT :email, :hash, TRUE, 0, CURRENT_TIMESTAMP
            WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = :email)
            """
        ),
        {"email": SYSTEM_EMAIL, "hash": "system-placeholder-password"},
    )
    row = bind.execute(sa.text("SELECT id FROM users WHERE email = :email LIMIT 1"), {"email": SYSTEM_EMAIL}).first()
    if row is None:
        raise RuntimeError("Failed to create system user for tenancy backfill")
    return int(row[0])


def upgrade() -> None:
    bind = op.get_bind()
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default=sa.text('0')))

    system_user_id = _ensure_system_user(bind)

    tenant_tables = [
        ('user_profiles', 'id'),
        ('user_preferences', 'id'),
        ('resume_versions', 'id'),
        ('applications', 'id'),
        ('student_profiles', 'id'),
        ('university_match_cache', 'id'),
        ('student_program_matches', 'id'),
        ('saved_programs', 'id'),
        ('applications_study', 'id'),
    ]

    for table_name, _pk in tenant_tables:
        op.add_column(table_name, sa.Column('user_id', sa.Integer(), nullable=True))

    for table_name, _pk in tenant_tables:
        bind.execute(sa.text(f"UPDATE {table_name} SET user_id = :user_id WHERE user_id IS NULL"), {"user_id": system_user_id})

    for table_name, _pk in tenant_tables:
        op.alter_column(table_name, 'user_id', existing_type=sa.Integer(), nullable=False)
        op.create_index(op.f(f'ix_{table_name}_user_id'), table_name, ['user_id'], unique=False)
        op.create_foreign_key(f'fk_{table_name}_user_id_users', table_name, 'users', ['user_id'], ['id'], ondelete='CASCADE')

    op.create_unique_constraint('uq_user_preferences_user_id', 'user_preferences', ['user_id'])


def downgrade() -> None:
    op.drop_constraint('uq_user_preferences_user_id', 'user_preferences', type_='unique')

    for table_name in [
        'applications_study',
        'saved_programs',
        'student_program_matches',
        'university_match_cache',
        'student_profiles',
        'applications',
        'resume_versions',
        'user_preferences',
        'user_profiles',
    ]:
        op.drop_constraint(f'fk_{table_name}_user_id_users', table_name, type_='foreignkey')
        op.drop_index(f'ix_{table_name}_user_id', table_name=table_name)
        op.drop_column(table_name, 'user_id')

    op.drop_column('users', 'token_version')
