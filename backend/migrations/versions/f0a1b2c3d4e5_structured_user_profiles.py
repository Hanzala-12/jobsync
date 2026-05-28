"""structured user profiles

Revision ID: f0a1b2c3d4e5
Revises: m20260524_merge_heads
Create Date: 2026-05-26 00:00:00.000000
"""
from __future__ import annotations

import json
import re
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "m20260524_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _normalize_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        raw_items = list(value)
    else:
        text = str(value).strip()
        if not text:
            return []
        if text.startswith("["):
            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    raw_items = parsed
                else:
                    raw_items = [text]
            except Exception:
                raw_items = re.split(r"[,;|\n]+", text)
        else:
            raw_items = re.split(r"[,;|\n]+", text)
    cleaned: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = str(item).strip()
        if not text:
            continue
        lowered = text.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        cleaned.append(text)
    return cleaned


def _ensure_column(table_name: str, column: sa.Column) -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {col["name"] for col in inspector.get_columns(table_name)}
    if column.name not in columns:
        op.add_column(table_name, column)


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("user_profiles"):
        existing_columns = {col["name"] for col in inspector.get_columns("user_profiles")}
        for column in [
            sa.Column("full_name", sa.String(), nullable=True),
            sa.Column("email", sa.String(), nullable=True),
            sa.Column("phone", sa.String(), nullable=True),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("linkedin_url", sa.String(), nullable=True),
            sa.Column("portfolio_url", sa.String(), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("achievements", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("preferred_job_titles", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("desired_salary_min", sa.Integer(), nullable=True),
            sa.Column("desired_salary_max", sa.Integer(), nullable=True),
            sa.Column("willing_to_relocate", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("preferred_work_location", sa.String(), nullable=True),
        ]:
            if column.name not in existing_columns:
                op.add_column("user_profiles", column)

        if "skills" in existing_columns:
            rows = bind.execute(sa.text("SELECT id, skills FROM user_profiles")).fetchall()
            for row in rows:
                normalized = json.dumps(_normalize_list(row.skills))
                bind.execute(
                    sa.text("UPDATE user_profiles SET skills = :skills WHERE id = :id"),
                    {"skills": normalized, "id": row.id},
                )
            op.alter_column(
                "user_profiles",
                "skills",
                existing_type=sa.Text(),
                type_=sa.JSON(),
                nullable=False,
                postgresql_using="skills::json",
            )
        else:
            op.add_column("user_profiles", sa.Column("skills", sa.JSON(), nullable=False, server_default=sa.text("'[]'")))

    if inspector.has_table("user_educations") is False:
        op.create_table(
            "user_educations",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("degree", sa.String(), nullable=True),
            sa.Column("institution", sa.String(), nullable=True),
            sa.Column("field_of_study", sa.String(), nullable=True),
            sa.Column("start_year", sa.Integer(), nullable=True),
            sa.Column("end_year", sa.Integer(), nullable=True),
            sa.Column("gpa", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
        )
        op.create_index(op.f("ix_user_educations_id"), "user_educations", ["id"], unique=False)
        op.create_index(op.f("ix_user_educations_profile_id"), "user_educations", ["profile_id"], unique=False)

    if inspector.has_table("user_work_experiences") is False:
        op.create_table(
            "user_work_experiences",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("job_title", sa.String(), nullable=True),
            sa.Column("company", sa.String(), nullable=True),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("start_date", sa.String(), nullable=True),
            sa.Column("end_date", sa.String(), nullable=True),
            sa.Column("responsibilities", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("achievements", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
        )
        op.create_index(op.f("ix_user_work_experiences_id"), "user_work_experiences", ["id"], unique=False)
        op.create_index(op.f("ix_user_work_experiences_profile_id"), "user_work_experiences", ["profile_id"], unique=False)

    if inspector.has_table("user_certifications") is False:
        op.create_table(
            "user_certifications",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("issuing_org", sa.String(), nullable=True),
            sa.Column("date_earned", sa.String(), nullable=True),
            sa.Column("credential_url", sa.String(), nullable=True),
        )
        op.create_index(op.f("ix_user_certifications_id"), "user_certifications", ["id"], unique=False)
        op.create_index(op.f("ix_user_certifications_profile_id"), "user_certifications", ["profile_id"], unique=False)

    if inspector.has_table("user_projects") is False:
        op.create_table(
            "user_projects",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("technologies", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
            sa.Column("project_url", sa.String(), nullable=True),
        )
        op.create_index(op.f("ix_user_projects_id"), "user_projects", ["id"], unique=False)
        op.create_index(op.f("ix_user_projects_profile_id"), "user_projects", ["profile_id"], unique=False)

    if inspector.has_table("user_languages") is False:
        op.create_table(
            "user_languages",
            sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
            sa.Column("profile_id", sa.Integer(), sa.ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(), nullable=True),
            sa.Column("proficiency", sa.String(), nullable=True),
        )
        op.create_index(op.f("ix_user_languages_id"), "user_languages", ["id"], unique=False)
        op.create_index(op.f("ix_user_languages_profile_id"), "user_languages", ["profile_id"], unique=False)

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("user_preferences")}
    if "fk_user_preferences_selected_profile_id_user_profiles" not in fk_names:
        op.create_foreign_key(
            "fk_user_preferences_selected_profile_id_user_profiles",
            "user_preferences",
            "user_profiles",
            ["selected_profile_id"],
            ["id"],
            source_schema=None,
            referent_schema=None,
            ondelete="SET NULL",
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if inspector.has_table("user_languages"):
        op.drop_index(op.f("ix_user_languages_profile_id"), table_name="user_languages")
        op.drop_index(op.f("ix_user_languages_id"), table_name="user_languages")
        op.drop_table("user_languages")
    if inspector.has_table("user_projects"):
        op.drop_index(op.f("ix_user_projects_profile_id"), table_name="user_projects")
        op.drop_index(op.f("ix_user_projects_id"), table_name="user_projects")
        op.drop_table("user_projects")
    if inspector.has_table("user_certifications"):
        op.drop_index(op.f("ix_user_certifications_profile_id"), table_name="user_certifications")
        op.drop_index(op.f("ix_user_certifications_id"), table_name="user_certifications")
        op.drop_table("user_certifications")
    if inspector.has_table("user_work_experiences"):
        op.drop_index(op.f("ix_user_work_experiences_profile_id"), table_name="user_work_experiences")
        op.drop_index(op.f("ix_user_work_experiences_id"), table_name="user_work_experiences")
        op.drop_table("user_work_experiences")
    if inspector.has_table("user_educations"):
        op.drop_index(op.f("ix_user_educations_profile_id"), table_name="user_educations")
        op.drop_index(op.f("ix_user_educations_id"), table_name="user_educations")
        op.drop_table("user_educations")

    fk_names = {fk["name"] for fk in inspector.get_foreign_keys("user_preferences")}
    if "fk_user_preferences_selected_profile_id_user_profiles" in fk_names:
        op.drop_constraint("fk_user_preferences_selected_profile_id_user_profiles", "user_preferences", type_="foreignkey")

    if inspector.has_table("user_profiles"):
        existing_columns = {col["name"] for col in inspector.get_columns("user_profiles")}
        if "skills" in existing_columns:
            rows = bind.execute(sa.text("SELECT id, skills FROM user_profiles")).fetchall()
            for row in rows:
                normalized = ", ".join(_normalize_list(row.skills))
                bind.execute(
                    sa.text("UPDATE user_profiles SET skills = :skills WHERE id = :id"),
                    {"skills": normalized, "id": row.id},
                )
            op.alter_column(
                "user_profiles",
                "skills",
                existing_type=sa.JSON(),
                type_=sa.Text(),
                nullable=True,
                postgresql_using="skills::text",
            )
        for column_name in [
            "full_name",
            "email",
            "phone",
            "location",
            "linkedin_url",
            "portfolio_url",
            "summary",
            "achievements",
            "preferred_job_titles",
            "desired_salary_min",
            "desired_salary_max",
            "willing_to_relocate",
            "preferred_work_location",
        ]:
            if column_name in existing_columns:
                op.drop_column("user_profiles", column_name)
