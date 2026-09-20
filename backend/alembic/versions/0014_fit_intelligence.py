"""Phase 2 - Evidence-grounded job matching intelligence tables

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-24

Creates:
- job_requirement_extractions: cached structured JD requirement extraction
  (one row per job; keyed by job version + extractor version).
- job_fit_analyses: persisted requirement-level fit analysis per
  (job, candidate) with the full evidence payload stored as JSON.
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "job_requirement_extractions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("job_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("extractor_version", sa.String(20), nullable=False),
        sa.Column("requirements", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_job_requirement_extractions_job_id"),
        "job_requirement_extractions", ["job_id"], unique=True,
    )

    op.create_table(
        "job_fit_analyses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=True),
        sa.Column("overall_fit", sa.String(30), nullable=False),
        sa.Column("fit_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("engine_version", sa.String(20), nullable=False),
        sa.Column("job_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_job_fit_job_candidate"),
    )
    op.create_index(op.f("ix_job_fit_analyses_job_id"), "job_fit_analyses", ["job_id"], unique=False)
    op.create_index(op.f("ix_job_fit_analyses_candidate_id"), "job_fit_analyses", ["candidate_id"], unique=False)


def downgrade() -> None:
    op.drop_table("job_fit_analyses")
    op.drop_table("job_requirement_extractions")
