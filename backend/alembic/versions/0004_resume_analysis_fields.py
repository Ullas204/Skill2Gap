"""add analysis fields to resume_analysis

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-09
"""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("resume_analysis", sa.Column("completeness_score", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("resume_analysis", sa.Column("readability_score", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("resume_analysis", sa.Column("professionalism_score", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("resume_analysis", sa.Column("keyword_optimization_score", sa.Integer(), server_default=sa.text("0"), nullable=False))
    op.add_column("resume_analysis", sa.Column("skill_analysis", sa.JSON(), nullable=True))
    op.add_column("resume_analysis", sa.Column("industry_keywords", sa.JSON(), nullable=True))
    op.add_column("resume_analysis", sa.Column("strengths", sa.JSON(), nullable=True))
    op.add_column("resume_analysis", sa.Column("weaknesses", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("resume_analysis", "weaknesses")
    op.drop_column("resume_analysis", "strengths")
    op.drop_column("resume_analysis", "industry_keywords")
    op.drop_column("resume_analysis", "skill_analysis")
    op.drop_column("resume_analysis", "keyword_optimization_score")
    op.drop_column("resume_analysis", "professionalism_score")
    op.drop_column("resume_analysis", "readability_score")
    op.drop_column("resume_analysis", "completeness_score")
