"""add screening_results, candidate_rankings, skill_gap_analyses tables

Revision ID: 0006
Revises: 0005
Create Date: 2026-07-18
"""

import sqlalchemy as sa
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "screening_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("resume_id", sa.Uuid(), sa.ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True),
        sa.Column("overall_match_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("skill_match_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("experience_match_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("education_match_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("project_match_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("certification_match_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("location_match_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("employment_type_match_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("semantic_match_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("matched_skills", sa.JSON(), nullable=True),
        sa.Column("missing_required_skills", sa.JSON(), nullable=True),
        sa.Column("missing_preferred_skills", sa.JSON(), nullable=True),
        sa.Column("strengths", sa.JSON(), nullable=True),
        sa.Column("weaknesses", sa.JSON(), nullable=True),
        sa.Column("recommendation", sa.String(30), server_default="consider", nullable=False),
        sa.Column("strength_level", sa.String(20), server_default="average", nullable=False),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_screening_job_candidate"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "candidate_rankings",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("job_id", sa.Uuid(), sa.ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("candidate_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("screening_result_id", sa.Uuid(), sa.ForeignKey("screening_results.id", ondelete="CASCADE"), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("previous_rank", sa.Integer(), nullable=True),
        sa.Column("rank_change", sa.Integer(), server_default="0", nullable=False),
        sa.Column("overall_score", sa.Integer(), server_default="0", nullable=False),
        sa.Column("strength_level", sa.String(20), server_default="average", nullable=False),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_ranking_job_candidate"),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "skill_gap_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("screening_result_id", sa.Uuid(), sa.ForeignKey("screening_results.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("missing_required_skills", sa.JSON(), nullable=True),
        sa.Column("missing_preferred_skills", sa.JSON(), nullable=True),
        sa.Column("experience_gap_description", sa.Text(), nullable=True),
        sa.Column("education_gap_description", sa.Text(), nullable=True),
        sa.Column("certification_gap_description", sa.Text(), nullable=True),
        sa.Column("skill_suggestions", sa.JSON(), nullable=True),
        sa.Column("improvement_suggestions", sa.JSON(), nullable=True),
        sa.Column("interview_readiness_score", sa.Integer(), server_default="0", nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("skill_gap_analyses")
    op.drop_table("candidate_rankings")
    op.drop_table("screening_results")
