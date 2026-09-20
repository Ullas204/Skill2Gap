"""Phase 14 (Simulation Intelligence) - Simulation execution, results & impacts

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-17

Creates:
- simulation_executions: one row per run of a simulation scenario. Holds the
  frozen configuration snapshot evaluated at run time, worker progress, status
  lifecycle (queued -> running -> completed/failed/cancelled) and the aggregate
  JSON summary produced by the engine. No live hiring data is ever written by
  an execution; all outputs below are simulation-only projections.
- simulation_results: one row per (execution, candidate). Stores the baseline
  vs scenario score/rank/qualification/shortlist outcomes plus per-dimension
  score contributions used to explain "why did this candidate move?".
- simulation_impacts: one row per aggregate metric describing the *effect* of
  the hypothetical configuration on the candidate pool (e.g. entered/left
  shortlist counts, average score change).
"""

import sqlalchemy as sa
from alembic import op

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "simulation_executions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(20), server_default="queued", nullable=False),
        sa.Column("progress", sa.Integer(), server_default="0", nullable=False),
        sa.Column("total_candidates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_candidates", sa.Integer(), server_default="0", nullable=False),
        sa.Column("engine_version", sa.String(30), nullable=False),
        sa.Column("configuration_snapshot", sa.JSON(), nullable=False),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["scenario_id"], ["simulation_scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_simulation_executions_scenario_id"),
        "simulation_executions", ["scenario_id"], unique=False,
    )
    op.create_index(
        op.f("ix_simulation_executions_status"),
        "simulation_executions", ["status"], unique=False,
    )
    op.create_index(
        op.f("ix_simulation_executions_job_id"),
        "simulation_executions", ["job_id"], unique=False,
    )

    op.create_table(
        "simulation_results",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_id", sa.Uuid(), nullable=False),
        sa.Column("candidate_name", sa.String(255), nullable=False),
        sa.Column("baseline_score", sa.Integer(), nullable=False),
        sa.Column("simulation_score", sa.Integer(), nullable=False),
        sa.Column("score_change", sa.Integer(), nullable=False),
        sa.Column("baseline_rank", sa.Integer(), nullable=False),
        sa.Column("simulation_rank", sa.Integer(), nullable=False),
        sa.Column("rank_change", sa.Integer(), nullable=False),
        sa.Column("baseline_status", sa.String(20), nullable=False),
        sa.Column("simulation_status", sa.String(20), nullable=False),
        sa.Column("baseline_shortlisted", sa.Boolean(), nullable=False),
        sa.Column("simulation_shortlisted", sa.Boolean(), nullable=False),
        sa.Column("baseline_dimensions", sa.JSON(), nullable=True),
        sa.Column("simulation_dimensions", sa.JSON(), nullable=True),
        sa.Column("reason", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["simulation_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scenario_id"], ["simulation_scenarios.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["candidate_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id", "candidate_id", name="uq_execution_candidate"),
    )
    op.create_index(
        op.f("ix_simulation_results_execution_id"),
        "simulation_results", ["execution_id"], unique=False,
    )
    op.create_index(
        op.f("ix_simulation_results_scenario_id"),
        "simulation_results", ["scenario_id"], unique=False,
    )
    op.create_index(
        op.f("ix_simulation_results_candidate_id"),
        "simulation_results", ["candidate_id"], unique=False,
    )

    op.create_table(
        "simulation_impacts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("execution_id", sa.Uuid(), nullable=False),
        sa.Column("scenario_id", sa.Uuid(), nullable=False),
        sa.Column("metric", sa.String(80), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("simulation_value", sa.Float(), nullable=False),
        sa.Column("change_value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["execution_id"], ["simulation_executions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["scenario_id"], ["simulation_scenarios.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_id", "metric", name="uq_execution_metric"),
    )
    op.create_index(
        op.f("ix_simulation_impacts_execution_id"),
        "simulation_impacts", ["execution_id"], unique=False,
    )


def downgrade() -> None:
    op.drop_table("simulation_impacts")
    op.drop_table("simulation_results")
    op.drop_table("simulation_executions")