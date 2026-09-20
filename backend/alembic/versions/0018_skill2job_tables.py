"""Skill2Job Agentic Career Intelligence - 8 core tables

Revision ID: 0018
Revises: 0017
Create Date: 2026-09-20

Creates:
- skill2job_perceptions: candidate perception inputs (resume/text/voice/image)
- skill2job_profile_states: consolidated candidate profile state
- skill2job_jobs: curated local job catalog
- skill2job_job_matches: per-candidate job match scores
- skill2job_skill_gaps: per-(candidate, job) gap analysis
- skill2job_simulations: what-if opportunity simulations
- skill2job_training_progress: candidate training module progress
- skill2job_execution_traces: LangGraph pipeline run traces
"""

import sqlalchemy as sa
from alembic import op

revision = "0018"
down_revision = "0017"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- skill2job_perceptions ---
    op.create_table(
        "skill2job_perceptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("input_type", sa.String(30), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=True),
        sa.Column("file_type", sa.String(20), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("stored_path", sa.String(500), nullable=True),
        sa.Column("processing_status", sa.String(20), server_default="ok", nullable=False),
        sa.Column("processing_message", sa.Text(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("warnings", sa.JSON(), nullable=True),
        sa.Column("parser_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_s2j_perception_user_created"),
        "skill2job_perceptions", ["user_id", "created_at"], unique=False,
    )
    op.create_index(
        op.f("ix_skill2job_perceptions_processing_status"),
        "skill2job_perceptions", ["processing_status"], unique=False,
    )

    # --- skill2job_profile_states ---
    op.create_table(
        "skill2job_profile_states",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("normalized_profile", sa.JSON(), nullable=True),
        sa.Column("skill_evidence", sa.JSON(), nullable=True),
        sa.Column("completeness", sa.JSON(), nullable=True),
        sa.Column("corrections", sa.JSON(), nullable=True),
        sa.Column("scoring_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_s2j_profile_user"),
    )

    # --- skill2job_jobs ---
    op.create_table(
        "skill2job_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("remote_type", sa.String(40), nullable=True),
        sa.Column("employment_type", sa.String(40), nullable=True),
        sa.Column("experience_required", sa.String(255), nullable=True),
        sa.Column("education_required", sa.String(255), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skills", sa.JSON(), nullable=True),
        sa.Column("preferred_skills", sa.JSON(), nullable=True),
        sa.Column("salary_range", sa.String(255), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(10), server_default="USD", nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("source_url", sa.String(500), nullable=True),
        sa.Column("external_id", sa.String(255), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("active", sa.Boolean(), server_default="1", nullable=False),
        sa.Column("ai_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "external_id", name="uq_s2j_job_source_external"),
    )
    op.create_index(
        op.f("ix_s2j_job_active_title"),
        "skill2job_jobs", ["active", "title"], unique=False,
    )
    op.create_index(
        op.f("ix_skill2job_jobs_active"),
        "skill2job_jobs", ["active"], unique=False,
    )

    # --- skill2job_job_matches ---
    op.create_table(
        "skill2job_job_matches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("overall_score", sa.Integer(), nullable=False),
        sa.Column("skill_score", sa.Integer(), nullable=True),
        sa.Column("experience_score", sa.Integer(), nullable=True),
        sa.Column("education_score", sa.Integer(), nullable=True),
        sa.Column("project_score", sa.Integer(), nullable=True),
        sa.Column("certification_score", sa.Integer(), nullable=True),
        sa.Column("location_score", sa.Integer(), nullable=True),
        sa.Column("employment_type_score", sa.Integer(), nullable=True),
        sa.Column("semantic_score", sa.Integer(), nullable=True),
        sa.Column("matched_skills", sa.JSON(), nullable=True),
        sa.Column("missing_required", sa.JSON(), nullable=True),
        sa.Column("missing_preferred", sa.JSON(), nullable=True),
        sa.Column("transferable_skills", sa.JSON(), nullable=True),
        sa.Column("suggested_skills", sa.JSON(), nullable=True),
        sa.Column("recommendation", sa.String(30), nullable=False),
        sa.Column("strength_level", sa.String(20), nullable=False),
        sa.Column("match_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["skill2job_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_s2j_match_user_job"),
    )
    op.create_index(
        op.f("ix_s2j_match_user_score"),
        "skill2job_job_matches", ["user_id", "overall_score"], unique=False,
    )
    op.create_index(
        op.f("ix_skill2job_job_matches_user_id"),
        "skill2job_job_matches", ["user_id"], unique=False,
    )
    op.create_index(
        op.f("ix_skill2job_job_matches_overall_score"),
        "skill2job_job_matches", ["overall_score"], unique=False,
    )

    # --- skill2job_skill_gaps ---
    op.create_table(
        "skill2job_skill_gaps",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("analysis", sa.JSON(), nullable=False),
        sa.Column("analysis_version", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["skill2job_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "job_id", name="uq_s2j_gap_user_job"),
    )
    op.create_index(
        op.f("ix_s2j_gap_user"),
        "skill2job_skill_gaps", ["user_id"], unique=False,
    )

    # --- skill2job_simulations ---
    op.create_table(
        "skill2job_simulations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("dream_job_title", sa.String(255), nullable=True),
        sa.Column("skills_added", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_skill2job_simulations_user_id"),
        "skill2job_simulations", ["user_id"], unique=False,
    )

    # --- skill2job_training_progress ---
    op.create_table(
        "skill2job_training_progress",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("module_key", sa.String(255), nullable=False),
        sa.Column("skill", sa.String(255), nullable=False),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("provider", sa.String(255), nullable=False),
        sa.Column("url", sa.String(600), nullable=True),
        sa.Column("resource_type", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), server_default="in_progress", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "module_key", name="uq_s2j_training_user_module"),
    )
    op.create_index(
        op.f("ix_s2j_training_user"),
        "skill2job_training_progress", ["user_id"], unique=False,
    )

    # --- skill2job_execution_traces ---
    op.create_table(
        "skill2job_execution_traces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.String(128), nullable=False),
        sa.Column("trace", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_skill2job_execution_traces_user_id"),
        "skill2job_execution_traces", ["user_id"], unique=False,
    )
    op.create_index(
        op.f("ix_skill2job_execution_traces_run_id"),
        "skill2job_execution_traces", ["run_id"], unique=False,
    )


def downgrade() -> None:
    op.drop_table("skill2job_execution_traces")
    op.drop_table("skill2job_training_progress")
    op.drop_table("skill2job_simulations")
    op.drop_table("skill2job_skill_gaps")
    op.drop_table("skill2job_job_matches")
    op.drop_table("skill2job_jobs")
    op.drop_table("skill2job_profile_states")
    op.drop_table("skill2job_perceptions")
