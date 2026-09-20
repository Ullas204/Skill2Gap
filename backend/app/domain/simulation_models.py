"""SQLAlchemy models for Simulation Intelligence (Phases 1 & 3).

Phase 1 (scenarios): a SimulationScenario captures a hypothetical hiring
configuration that a recruiter/HR user wants to test against a real job. The
baseline configuration is snapshotted at creation time so later changes to the
job do not corrupt an already-created simulation.

Phase 3 (execution): SimulationExecution, SimulationResult and
SimulationImpact persist the real "what-if" run. An execution is a READ-ONLY
analytical layer over the live candidate pool — it snapshots the configuration
it evaluated and writes ONLY simulation-scoped rows (never JobDescription,
CandidateRanking, ScreeningResult, candidates or shortlists).
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import SimulationStatus


class SimulationScenario(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "simulation_scenarios"

    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default=SimulationStatus.DRAFT.value, nullable=False, index=True,
    )
    baseline_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    simulation_config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    config_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # DB column is named "metadata" (JSON) while the mapped attribute avoids
    # shadowing DeclarativeBase.metadata.
    metadata_json: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    organization: Mapped["Organization | None"] = relationship(
        "Organization", backref="simulation_scenarios",
    )
    job: Mapped["Job"] = relationship("Job", backref="simulation_scenarios")
    creator: Mapped["User"] = relationship(
        "User", foreign_keys=[created_by], backref="simulation_scenarios",
    )
    executions: Mapped[list["SimulationExecution"]] = relationship(
        "SimulationExecution", back_populates="scenario", cascade="all, delete-orphan",
    )


class SimulationExecution(Base, UUIDMixin, TimestampMixin):
    """One execution of a simulation scenario against the live candidate pool.

    The `configuration_snapshot` captures exactly what was evaluated: the
    baseline + hypothetical configuration plus the job context and the
    candidate pool. Re-running a scenario creates a fresh execution row, so
    every run is reproducible and auditable. Status lifecycle is driven by the
    engine: queued -> running -> completed (or failed/cancelled).
    """

    __tablename__ = "simulation_executions"

    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_scenarios.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SimulationStatus.QUEUED.value, nullable=False, index=True,
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_candidates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    processed_candidates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    engine_version: Mapped[str] = mapped_column(String(30), nullable=False)
    configuration_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False)
    summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    scenario: Mapped["SimulationScenario"] = relationship(
        "SimulationScenario", back_populates="executions",
    )
    organization: Mapped["Organization | None"] = relationship("Organization")
    job: Mapped["Job"] = relationship("Job")
    creator: Mapped["User"] = relationship("User", foreign_keys=[created_by])
    results: Mapped[list["SimulationResult"]] = relationship(
        "SimulationResult", back_populates="execution", cascade="all, delete-orphan",
    )
    impacts: Mapped[list["SimulationImpact"]] = relationship(
        "SimulationImpact", back_populates="execution", cascade="all, delete-orphan",
    )


class SimulationResult(Base, UUIDMixin, TimestampMixin):
    """Per-candidate outcome of one simulation execution.

    All columns are baseline-vs-scenario projections. Nothing here touches live
    hiring records: baseline_* reflects the frozen job snapshot, simulation_*
    reflects the hypothetical configuration. `reason` is a short, human
    readable explanation of the dominant driver of the score change.
    """

    __tablename__ = "simulation_results"
    __table_args__ = (
        UniqueConstraint("execution_id", "candidate_id", name="uq_execution_candidate"),
    )

    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_executions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_scenarios.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    candidate_name: Mapped[str] = mapped_column(String(255), nullable=False)
    baseline_score: Mapped[int] = mapped_column(Integer, nullable=False)
    simulation_score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_change: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    simulation_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    rank_change: Mapped[int] = mapped_column(Integer, nullable=False)
    baseline_status: Mapped[str] = mapped_column(String(20), nullable=False)
    simulation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    baseline_shortlisted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    simulation_shortlisted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    baseline_dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    simulation_dimensions: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Phase 5: requirement satisfaction data for per-requirement impact analysis
    baseline_matched_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    simulation_matched_skills: Mapped[list | None] = mapped_column(JSON, nullable=True)
    baseline_missing_required: Mapped[list | None] = mapped_column(JSON, nullable=True)
    simulation_missing_required: Mapped[list | None] = mapped_column(JSON, nullable=True)
    baseline_missing_preferred: Mapped[list | None] = mapped_column(JSON, nullable=True)
    simulation_missing_preferred: Mapped[list | None] = mapped_column(JSON, nullable=True)
    candidate_experience_years: Mapped[float | None] = mapped_column(Float, nullable=True)
    candidate_degrees: Mapped[list | None] = mapped_column(JSON, nullable=True)

    execution: Mapped["SimulationExecution"] = relationship(
        "SimulationExecution", back_populates="results",
    )
    scenario: Mapped["SimulationScenario"] = relationship("SimulationScenario")
    candidate: Mapped["User"] = relationship("User")


class SimulationImpact(Base, UUIDMixin, TimestampMixin):
    """One aggregate metric describing the effect of the hypothetical config.

    `baseline_value` / `simulation_value` / `change_value` make each metric
    self-describing (e.g. qualified_count 3 -> 7 -> +4). A metric has a stable
    name so API consumers and the UI can render a summary without re-calculating.
    """

    __tablename__ = "simulation_impacts"
    __table_args__ = (
        UniqueConstraint("execution_id", "metric", name="uq_execution_metric"),
    )

    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_executions.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    scenario_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("simulation_scenarios.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    metric: Mapped[str] = mapped_column(String(80), nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    simulation_value: Mapped[float] = mapped_column(Float, nullable=False)
    change_value: Mapped[float] = mapped_column(Float, nullable=False)

    execution: Mapped["SimulationExecution"] = relationship(
        "SimulationExecution", back_populates="impacts",
    )
    scenario: Mapped["SimulationScenario"] = relationship("SimulationScenario")