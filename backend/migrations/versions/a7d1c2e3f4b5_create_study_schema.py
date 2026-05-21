"""create study schema from scratch

Revision ID: a7d1c2e3f4b5
Revises: e3b7c5d9a1f2
Create Date: 2026-05-21 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7d1c2e3f4b5'
down_revision: Union[str, Sequence[str], None] = 'b4c9d1a5f2e7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'universities',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('city', sa.String(), nullable=False),
        sa.Column('website', sa.String(), nullable=True),
        sa.Column('ranking', sa.String(), nullable=True),
        sa.Column('ranking_global', sa.Integer(), nullable=True),
        sa.Column('logo_url', sa.String(), nullable=True),
        sa.Column('acceptance_rate', sa.Float(), nullable=True),
        sa.Column('accreditation', sa.String(), nullable=True),
        sa.Column('student_population', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_universities_city'), 'universities', ['city'], unique=False)
    op.create_index(op.f('ix_universities_country'), 'universities', ['country'], unique=False)
    op.create_index(op.f('ix_universities_id'), 'universities', ['id'], unique=False)
    op.create_index(op.f('ix_universities_name'), 'universities', ['name'], unique=False)
    op.create_index(op.f('ix_universities_ranking'), 'universities', ['ranking'], unique=False)
    op.create_index(op.f('ix_universities_ranking_global'), 'universities', ['ranking_global'], unique=False)

    op.create_table(
        'programs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('university_id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('degree_level', sa.String(), nullable=False),
        sa.Column('duration_years', sa.Integer(), nullable=False),
        sa.Column('estimated_tuition_fees', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(length=10), nullable=False),
        sa.Column('min_gpa', sa.Float(), nullable=True),
        sa.Column('ranking_global', sa.Integer(), nullable=True),
        sa.Column('ranking_national', sa.Integer(), nullable=True),
        sa.Column('min_ielts', sa.Float(), nullable=True),
        sa.Column('min_toefl', sa.Integer(), nullable=True),
        sa.Column('application_deadline', sa.String(), nullable=True),
        sa.Column('semester_intake', sa.String(), nullable=True),
        sa.Column('living_cost_estimate', sa.Integer(), nullable=True),
        sa.Column('scholarship_available', sa.Boolean(), nullable=False),
        sa.Column('program_url', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_programs_degree_level'), 'programs', ['degree_level'], unique=False)
    op.create_index(op.f('ix_programs_id'), 'programs', ['id'], unique=False)
    op.create_index(op.f('ix_programs_name'), 'programs', ['name'], unique=False)
    op.create_index(op.f('ix_programs_semester_intake'), 'programs', ['semester_intake'], unique=False)
    op.create_index(op.f('ix_programs_university_id'), 'programs', ['university_id'], unique=False)
    op.create_index(op.f('ix_programs_ranking_global'), 'programs', ['ranking_global'], unique=False)
    op.create_index(op.f('ix_programs_ranking_national'), 'programs', ['ranking_national'], unique=False)

    op.create_table(
        'student_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('gpa', sa.Float(), nullable=False),
        sa.Column('gre_score', sa.Integer(), nullable=True),
        sa.Column('toefl_score', sa.Integer(), nullable=True),
        sa.Column('ielts_score', sa.Float(), nullable=True),
        sa.Column('budget_per_year', sa.Integer(), nullable=False),
        sa.Column('preferred_countries', sa.JSON(), nullable=False),
        sa.Column('intended_major', sa.String(), nullable=False),
        sa.Column('degree_level', sa.String(), nullable=False),
        sa.Column('academic_background', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_student_profiles_degree_level'), 'student_profiles', ['degree_level'], unique=False)
    op.create_index(op.f('ix_student_profiles_id'), 'student_profiles', ['id'], unique=False)
    op.create_index(op.f('ix_student_profiles_intended_major'), 'student_profiles', ['intended_major'], unique=False)

    op.create_table(
        'scholarships',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('university_id', sa.Integer(), nullable=False),
        sa.Column('amount_usd', sa.Integer(), nullable=True),
        sa.Column('deadline', sa.String(), nullable=True),
        sa.Column('eligibility_criteria', sa.Text(), nullable=True),
        sa.Column('application_url', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['university_id'], ['universities.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_scholarships_id'), 'scholarships', ['id'], unique=False)
    op.create_index(op.f('ix_scholarships_name'), 'scholarships', ['name'], unique=False)
    op.create_index(op.f('ix_scholarships_university_id'), 'scholarships', ['university_id'], unique=False)

    op.create_table(
        'saved_programs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('saved_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['student_id'], ['student_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_saved_programs_id'), 'saved_programs', ['id'], unique=False)
    op.create_index(op.f('ix_saved_programs_program_id'), 'saved_programs', ['program_id'], unique=False)
    op.create_index(op.f('ix_saved_programs_student_id'), 'saved_programs', ['student_id'], unique=False)

    op.create_table(
        'applications_study',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='saved'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('applied_at', sa.DateTime(), nullable=True),
        sa.Column('deadline', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('(CURRENT_TIMESTAMP)')),
        sa.ForeignKeyConstraint(['student_id'], ['student_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_applications_study_id'), 'applications_study', ['id'], unique=False)
    op.create_index(op.f('ix_applications_study_program_id'), 'applications_study', ['program_id'], unique=False)
    op.create_index(op.f('ix_applications_study_status'), 'applications_study', ['status'], unique=False)
    op.create_index(op.f('ix_applications_study_student_id'), 'applications_study', ['student_id'], unique=False)

    op.create_table(
        'student_program_matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('match_score', sa.Integer(), nullable=False),
        sa.Column('academic_fit', sa.Integer(), nullable=False),
        sa.Column('budget_fit', sa.Integer(), nullable=False),
        sa.Column('location_fit', sa.Integer(), nullable=False),
        sa.Column('missing_requirements', sa.JSON(), nullable=False),
        sa.Column('strengths', sa.JSON(), nullable=False),
        sa.Column('recommendations', sa.JSON(), nullable=False),
        sa.Column('summary', sa.String(length=500), nullable=False),
        sa.Column('computed_at', sa.DateTime(), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['student_id'], ['student_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_id', 'program_id', name='uq_student_program_matches_lookup'),
    )
    op.create_index(op.f('ix_student_program_matches_expires_at'), 'student_program_matches', ['expires_at'], unique=False)
    op.create_index(op.f('ix_student_program_matches_id'), 'student_program_matches', ['id'], unique=False)
    op.create_index(op.f('ix_student_program_matches_program_id'), 'student_program_matches', ['program_id'], unique=False)
    op.create_index(op.f('ix_student_program_matches_student_id'), 'student_program_matches', ['student_id'], unique=False)

    op.create_table(
        'university_match_cache',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('student_profile_id', sa.Integer(), nullable=False),
        sa.Column('program_id', sa.Integer(), nullable=False),
        sa.Column('intended_major', sa.String(), nullable=False),
        sa.Column('match_score', sa.Integer(), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('source_ids', sa.JSON(), nullable=False),
        sa.Column('cached_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['student_profile_id'], ['student_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['program_id'], ['programs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('student_profile_id', 'program_id', 'intended_major', name='uq_university_match_cache_lookup'),
    )
    op.create_index(op.f('ix_university_match_cache_expires_at'), 'university_match_cache', ['expires_at'], unique=False)
    op.create_index(op.f('ix_university_match_cache_id'), 'university_match_cache', ['id'], unique=False)
    op.create_index(op.f('ix_university_match_cache_intended_major'), 'university_match_cache', ['intended_major'], unique=False)
    op.create_index(op.f('ix_university_match_cache_program_id'), 'university_match_cache', ['program_id'], unique=False)
    op.create_index(op.f('ix_university_match_cache_student_profile_id'), 'university_match_cache', ['student_profile_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_university_match_cache_student_profile_id'), table_name='university_match_cache')
    op.drop_index(op.f('ix_university_match_cache_program_id'), table_name='university_match_cache')
    op.drop_index(op.f('ix_university_match_cache_intended_major'), table_name='university_match_cache')
    op.drop_index(op.f('ix_university_match_cache_id'), table_name='university_match_cache')
    op.drop_index(op.f('ix_university_match_cache_expires_at'), table_name='university_match_cache')
    op.drop_table('university_match_cache')

    op.drop_index(op.f('ix_student_program_matches_student_id'), table_name='student_program_matches')
    op.drop_index(op.f('ix_student_program_matches_program_id'), table_name='student_program_matches')
    op.drop_index(op.f('ix_student_program_matches_id'), table_name='student_program_matches')
    op.drop_index(op.f('ix_student_program_matches_expires_at'), table_name='student_program_matches')
    op.drop_table('student_program_matches')

    op.drop_index(op.f('ix_applications_study_student_id'), table_name='applications_study')
    op.drop_index(op.f('ix_applications_study_status'), table_name='applications_study')
    op.drop_index(op.f('ix_applications_study_program_id'), table_name='applications_study')
    op.drop_index(op.f('ix_applications_study_id'), table_name='applications_study')
    op.drop_table('applications_study')

    op.drop_index(op.f('ix_saved_programs_student_id'), table_name='saved_programs')
    op.drop_index(op.f('ix_saved_programs_program_id'), table_name='saved_programs')
    op.drop_index(op.f('ix_saved_programs_id'), table_name='saved_programs')
    op.drop_table('saved_programs')

    op.drop_index(op.f('ix_scholarships_university_id'), table_name='scholarships')
    op.drop_index(op.f('ix_scholarships_name'), table_name='scholarships')
    op.drop_index(op.f('ix_scholarships_id'), table_name='scholarships')
    op.drop_table('scholarships')

    op.drop_index(op.f('ix_student_profiles_intended_major'), table_name='student_profiles')
    op.drop_index(op.f('ix_student_profiles_id'), table_name='student_profiles')
    op.drop_index(op.f('ix_student_profiles_degree_level'), table_name='student_profiles')
    op.drop_table('student_profiles')

    op.drop_index(op.f('ix_programs_ranking_national'), table_name='programs')
    op.drop_index(op.f('ix_programs_ranking_global'), table_name='programs')
    op.drop_index(op.f('ix_programs_university_id'), table_name='programs')
    op.drop_index(op.f('ix_programs_semester_intake'), table_name='programs')
    op.drop_index(op.f('ix_programs_name'), table_name='programs')
    op.drop_index(op.f('ix_programs_id'), table_name='programs')
    op.drop_index(op.f('ix_programs_degree_level'), table_name='programs')
    op.drop_table('programs')

    op.drop_index(op.f('ix_universities_ranking_global'), table_name='universities')
    op.drop_index(op.f('ix_universities_ranking'), table_name='universities')
    op.drop_index(op.f('ix_universities_name'), table_name='universities')
    op.drop_index(op.f('ix_universities_id'), table_name='universities')
    op.drop_index(op.f('ix_universities_country'), table_name='universities')
    op.drop_index(op.f('ix_universities_city'), table_name='universities')
    op.drop_table('universities')