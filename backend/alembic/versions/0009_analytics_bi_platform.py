"""Phase 9 - Enterprise Workforce Analytics & BI Platform

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-22
"""
from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ─── analytics_reports ────────────────────────────────────────
    op.create_table(
        "analytics_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("report_type", sa.String(30), nullable=False),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("is_scheduled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("schedule_cron", sa.String(100), nullable=True),
        sa.Column("last_generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_reports_user_id", "analytics_reports", ["user_id"])

    # ─── dashboard_layouts ────────────────────────────────────────
    op.create_table(
        "dashboard_layouts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("dashboard_key", sa.String(100), nullable=False),
        sa.Column("layout_config", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_dashboard_layouts_user_id", "dashboard_layouts", ["user_id"])

    # ─── alert_rules ──────────────────────────────────────────────
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("alert_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("condition_config", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("threshold", sa.Integer(), nullable=True),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_alert_rules_user_id", "alert_rules", ["user_id"])

    # ─── scheduled_reports ────────────────────────────────────────
    op.create_table(
        "scheduled_reports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("report_id", sa.Uuid(), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("export_format", sa.String(20), nullable=False),
        sa.Column("recipients", sa.JSON(), nullable=True),
        sa.Column("frequency", sa.String(50), nullable=False),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["report_id"], ["analytics_reports.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scheduled_reports_user_id", "scheduled_reports", ["user_id"])

    # ─── analytics_insights ───────────────────────────────────────
    op.create_table(
        "analytics_insights",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("insight_type", sa.String(30), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("data_payload", sa.JSON(), nullable=True),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("target_roles", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_analytics_insights_insight_type", "analytics_insights", ["insight_type"])


def downgrade() -> None:
    op.drop_table("analytics_insights")
    op.drop_table("scheduled_reports")
    op.drop_table("alert_rules")
    op.drop_table("dashboard_layouts")
    op.drop_table("analytics_reports")
