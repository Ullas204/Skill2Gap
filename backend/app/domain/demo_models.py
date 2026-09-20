"""SQLAlchemy models for the AI Demo Data Generator & Recruitment Simulation Platform."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class DemoScenario(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "demo_scenarios"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tags: Mapped[list | None] = mapped_column(JSON, nullable=True)

    runs: Mapped[list["DemoRun"]] = relationship(
        "DemoRun", back_populates="scenario", cascade="all, delete-orphan",
    )


class DemoCompany(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "demo_companies"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    industry: Mapped[str] = mapped_column(String(255), nullable=False)
    headquarters: Mapped[str | None] = mapped_column(String(255), nullable=True)
    size_range: Mapped[str | None] = mapped_column(String(100), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class DemoRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "demo_runs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    scenario_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("demo_scenarios.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    current_stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stage_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", backref="demo_runs")
    scenario: Mapped["DemoScenario | None"] = relationship("DemoScenario", back_populates="runs")
    events: Mapped[list["SimulationEvent"]] = relationship(
        "SimulationEvent", back_populates="run", cascade="all, delete-orphan",
        order_by="SimulationEvent.created_at",
    )


class SimulationEvent(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "simulation_events"

    run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("demo_runs.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)
    event_type: Mapped[str] = mapped_column(String(20), default="info", nullable=False)
    message: Mapped[str] = mapped_column(String(500), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    run: Mapped["DemoRun"] = relationship("DemoRun", back_populates="events")
