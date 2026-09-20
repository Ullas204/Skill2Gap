"""add jobs, job_applications, saved_jobs, recruiter_notes tables

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recruiter_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255), nullable=False),
        sa.Column("department", sa.String(255), nullable=True),
        sa.Column("employment_type", sa.String(50), nullable=False),
        sa.Column("experience_required", sa.String(255), nullable=True),
        sa.Column("education_required", sa.String(255), nullable=True),
        sa.Column("required_skills", sa.JSON(), nullable=False),
        sa.Column("preferred_skills", sa.JSON(), nullable=True),
        sa.Column("location", sa.String(255), nullable=False),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("salary_currency", sa.String(10), server_default=sa.text("'USD'"), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("benefits", sa.Text(), nullable=True),
        sa.Column("application_deadline", sa.Date(), nullable=True),
        sa.Column("status", sa.String(20), server_default=sa.text("'draft'"), nullable=False),
        sa.Column("is_archived", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["recruiter_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_jobs_recruiter_id"), "jobs", ["recruiter_id"], unique=False)

    op.create_table(
        "job_applications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=True),
        sa.Column("cover_letter", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default=sa.text("'applied'"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "candidate_id", name="uq_job_candidate"),
    )
    op.create_index(op.f("ix_job_applications_job_id"), "job_applications", ["job_id"], unique=False)
    op.create_index(op.f("ix_job_applications_candidate_id"), "job_applications", ["candidate_id"], unique=False)

    op.create_table(
        "recruiter_notes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_application_id", sa.Uuid(), nullable=False),
        sa.Column("recruiter_id", sa.Uuid(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["job_application_id"], ["job_applications.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recruiter_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_recruiter_notes_job_application_id"), "recruiter_notes", ["job_application_id"], unique=False)

    op.create_table(
        "saved_jobs",
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("candidate_id", "job_id"),
        sa.UniqueConstraint("candidate_id", "job_id", name="uq_candidate_saved_job"),
    )


def downgrade() -> None:
    op.drop_table("saved_jobs")
    op.drop_table("recruiter_notes")
    op.drop_table("job_applications")
    op.drop_table("jobs")
