"""Phase 1 - Enterprise Identity + Organization + Multi-Tenant Architecture

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-20

Migration Strategy:
- Adds new tables: organizations, organization_memberships, invitations
- Adds account_status column to users
- Adds organization_id column to jobs and audit_logs
- Adds event_type column to audit_logs
- Preserves all existing data
- Uses batch mode for SQLite compatibility on add_column with FK
- Idempotent: safe to re-run if partially applied
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name: str) -> bool:
    return inspect(bind).has_table(table_name)


def _column_exists(bind, table_name: str, column_name: str) -> bool:
    columns = {c["name"] for c in inspect(bind).get_columns(table_name)}
    return column_name in columns


def upgrade() -> None:
    bind = op.get_bind()

    # ── Organizations ────────────────────────────────────────────────
    if not _table_exists(bind, "organizations"):
        op.create_table(
            "organizations",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("slug", sa.String(100), nullable=False, unique=True, index=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("official_email", sa.String(255), nullable=True),
            sa.Column("domain", sa.String(255), nullable=True),
            sa.Column("logo_url", sa.String(500), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="active", index=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── Organization Memberships ─────────────────────────────────────
    if not _table_exists(bind, "organization_memberships"):
        op.create_table(
            "organization_memberships",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("role", sa.String(50), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="active"),
            sa.Column("invited_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
        )

    # ── Invitations ──────────────────────────────────────────────────
    if not _table_exists(bind, "invitations"):
        op.create_table(
            "invitations",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column("organization_id", sa.Uuid(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("invited_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("email", sa.String(255), nullable=False, index=True),
            sa.Column("role", sa.String(50), nullable=False),
            sa.Column("token_hash", sa.String(255), nullable=False, unique=True, index=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("accepted_by_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )

    # ── Users: add account_status (no FK, safe for SQLite) ──────────
    if not _column_exists(bind, "users", "account_status"):
        op.add_column("users", sa.Column("account_status", sa.String(30), nullable=False, server_default="active"))
        op.create_index("ix_users_account_status", "users", ["account_status"])

    # ── Jobs: add organization_id for tenant isolation ───────────────
    if not _column_exists(bind, "jobs", "organization_id"):
        with op.batch_alter_table("jobs") as batch_op:
            batch_op.add_column(sa.Column("organization_id", sa.Uuid(), nullable=True))
            batch_op.create_index("ix_jobs_organization_id", ["organization_id"])
            batch_op.create_foreign_key("fk_jobs_organization_id", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")

    # ── Audit Logs: add organization_id and event_type ───────────────
    if not _column_exists(bind, "audit_logs", "organization_id"):
        with op.batch_alter_table("audit_logs") as batch_op:
            batch_op.add_column(sa.Column("organization_id", sa.Uuid(), nullable=True))
            batch_op.create_index("ix_audit_logs_organization_id", ["organization_id"])
            batch_op.create_foreign_key("fk_audit_logs_organization_id", "organizations", ["organization_id"], ["id"], ondelete="SET NULL")

    if not _column_exists(bind, "audit_logs", "event_type"):
        with op.batch_alter_table("audit_logs") as batch_op:
            batch_op.add_column(sa.Column("event_type", sa.String(100), nullable=False, server_default="unknown"))
            batch_op.create_index("ix_audit_logs_event_type", ["event_type"])


def downgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.drop_index("ix_audit_logs_event_type")
        batch_op.drop_column("event_type")
        batch_op.drop_index("ix_audit_logs_organization_id")
        batch_op.drop_constraint("fk_audit_logs_organization_id", type_="foreignkey")
        batch_op.drop_column("organization_id")

    with op.batch_alter_table("jobs") as batch_op:
        batch_op.drop_index("ix_jobs_organization_id")
        batch_op.drop_constraint("fk_jobs_organization_id", type_="foreignkey")
        batch_op.drop_column("organization_id")

    op.drop_index("ix_users_account_status", table_name="users")
    op.drop_column("users", "account_status")
    op.drop_table("invitations")
    op.drop_table("organization_memberships")
    op.drop_table("organizations")
