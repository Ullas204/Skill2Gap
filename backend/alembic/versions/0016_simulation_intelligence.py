"""Phase 14 (Simulation Intelligence) - Simulation Scenario foundation

Revision ID: 0016
Revises: 0015
Create Date: 2026-09-17

Creates:
- simulation_scenarios: one row per hiring-simulation strategy sandbox entry
  created by recruiters/HR. Stores a frozen baseline snapshot of the target
  job's screening configuration plus the experiment's simulation configuration
  as JSON, along with lifecycle status. Phase 1 provides CRUD only; the
  simulation engine (scheduling, ranking, fairness, XAI) arrives in later
  phases and will transition statuses into the execution states.
"""

import sqlalchemy as sa
from alembic import op

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_scenarios",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), server_default="draft", nullable=False),
        sa.Column("baseline_config", sa.JSON(), nullable=False),
        sa.Column("simulation_config", sa.JSON(), nullable=True),
        sa.Column("config_version", sa.Integer(), server_default="1", nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_simulation_scenarios_organization_id"),
        "simulation_scenarios", ["organization_id"], unique=False,
    )
    op.create_index(
        op.f("ix_simulation_scenarios_job_id"),
        "simulation_scenarios", ["job_id"], unique=False,
    )
    op.create_index(
        op.f("ix_simulation_scenarios_created_by"),
        "simulation_scenarios", ["created_by"], unique=False,
    )
    op.create_index(
        op.f("ix_simulation_scenarios_status"),
        "simulation_scenarios", ["status"], unique=False,
    )


def downgrade() -> None:
    op.drop_table("simulation_scenarios")