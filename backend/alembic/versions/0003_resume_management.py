"""resume management tables

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resumes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("profile_id", sa.Uuid(), nullable=False),
        sa.Column("original_filename", sa.String(500), nullable=False),
        sa.Column("storage_path", sa.String(1000), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=True),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("status", sa.String(20), server_default=sa.text("'uploaded'"), nullable=False),
        sa.Column("language", sa.String(50), nullable=True),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["candidate_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_resumes_user_id"), "resumes", ["user_id"], unique=False)

    op.create_table(
        "parsed_resume_data",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column("parsed_json", sa.JSON(), nullable=True),
        sa.Column("personal_info", sa.JSON(), nullable=True),
        sa.Column("education", sa.JSON(), nullable=True),
        sa.Column("experience", sa.JSON(), nullable=True),
        sa.Column("skills", sa.JSON(), nullable=True),
        sa.Column("projects", sa.JSON(), nullable=True),
        sa.Column("certifications", sa.JSON(), nullable=True),
        sa.Column("languages", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_id"),
    )

    op.create_table(
        "resume_analysis",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=False),
        sa.Column("quality_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("ats_score", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("missing_sections", sa.JSON(), nullable=True),
        sa.Column("recommendations", sa.JSON(), nullable=True),
        sa.Column("section_scores", sa.JSON(), nullable=True),
        sa.Column("keyword_analysis", sa.JSON(), nullable=True),
        sa.Column("formatting_issues", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("resume_id"),
    )


def downgrade() -> None:
    op.drop_table("resume_analysis")
    op.drop_table("parsed_resume_data")
    op.drop_table("resumes")
