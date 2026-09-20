"""Phase 3 - Candidate evidence intelligence cache table

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-24

Creates:
- candidate_evidence_intels: one cached evidence-intelligence result per
  candidate (strengths, skill depth, review flags, screening questions,
  grounded summary) with the full payload stored as JSON. Regenerated when
  the resume changes or the engine version changes.
"""

import sqlalchemy as sa
from alembic import op

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "candidate_evidence_intels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("resume_id", sa.Uuid(), nullable=True),
        sa.Column("engine_version", sa.String(20), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["resume_id"], ["resumes.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_candidate_evidence_intels_candidate_id"),
        "candidate_evidence_intels", ["candidate_id"], unique=True,
    )


def downgrade() -> None:
    op.drop_table("candidate_evidence_intels")
