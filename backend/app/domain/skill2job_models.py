"""Skill2Job domain models.

Dedicated persistence for the Agentic Career Intelligence module. These live
next to the existing domain models but map to their own tables so the module
never mutates the recruiter-facing job/application/data.

Design rules:
- Nothing is invented. Missing information stays NULL / empty.
- Every derived artifact keeps its generating version so reprocessing is
  detectable and auditable.
- User-scoped rows are owned by the candidate (``user_id``) only.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Skill2JobPerception(Base, UUIDMixin, TimestampMixin):
    """A candidate's perception input (resume / document / free-text / voice / image).

    Stores the raw extraction result and per-field provenance. Voice and image
    inputs that lack a configured provider are persisted with
    ``processing_status = 'failed'`` and a human-readable message (never fake
    transcription).
    """

    __tablename__ = "skill2job_perceptions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    input_type: Mapped[str] = mapped_column(String(30), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    file_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    stored_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    processing_status: Mapped[str] = mapped_column(
        String(20), default="ok", nullable=False, index=True,
    )
    processing_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[dict] = mapped_column(JSON, nullable=True)
    warnings: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    parser_version: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        Index("ix_s2j_perception_user_created", "user_id", "created_at"),
    )


class Skill2JobProfileState(Base, UUIDMixin, TimestampMixin):
    """Consolidated candidate profile state produced by the Profile Agent.

    ``normalized_profile`` and friends are JSON snapshots so a candidate can be
    re-scored without relocating recruiter-facing data that already lives in
    ``candidate_profiles`` etc.
    """

    __tablename__ = "skill2job_profile_states"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True,
    )
    normalized_profile: Mapped[dict] = mapped_column(JSON, nullable=True)
    skill_evidence: Mapped[dict] = mapped_column(JSON, default=dict, nullable=True)
    completeness: Mapped[dict] = mapped_column(JSON, default=dict, nullable=True)
    corrections: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    scoring_version: Mapped[str] = mapped_column(String(50), nullable=False)


class Skill2JobJob(Base, UUIDMixin, TimestampMixin):
    """Curated / locally-observed job catalog entry.

    Deliberately separate from ``jobs`` (recruiter-owned, tenant-scoped) so the
    matching engine can train on a per-candidate local market without polluting
    recruiter dashboards. Attribute names mirror the field contract used by
    ``JobRequirementExtractor`` (description / required_skills / preferred_skills /
    experience_required / education_required) for reuse.
    """

    __tablename__ = "skill2job_jobs"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company: Mapped[str] = mapped_column(String(255), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remote_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    experience_required: Mapped[str | None] = mapped_column(String(255), nullable=True)
    education_required: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    required_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    preferred_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    salary_range: Mapped[str | None] = mapped_column(String(255), nullable=True)
    salary_min: Mapped[int | None] = mapped_column(nullable=True)
    salary_max: Mapped[int | None] = mapped_column(nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD", nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_s2j_job_source_external"),
        Index("ix_s2j_job_active_title", "active", "title"),
    )


class Skill2JobJobMatch(Base, UUIDMixin, TimestampMixin):
    """Persisted per-candidate job match produced by the Matching Agent.

    Mirrors the existing ``MatchingEngine`` score components so candidates can
    see exactly why a curated opportunity was ranked (deterministic, auditable,
    nothing invented: every score component is computed from the shared engine).
    """

    __tablename__ = "skill2job_job_matches"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skill2job_jobs.id", ondelete="CASCADE"), nullable=False,
    )
    overall_score: Mapped[int] = mapped_column(nullable=False, index=True)
    skill_score: Mapped[int] = mapped_column(default=0, nullable=True)
    experience_score: Mapped[int] = mapped_column(default=0, nullable=True)
    education_score: Mapped[int] = mapped_column(default=0, nullable=True)
    project_score: Mapped[int] = mapped_column(default=0, nullable=True)
    certification_score: Mapped[int] = mapped_column(default=0, nullable=True)
    location_score: Mapped[int] = mapped_column(default=0, nullable=True)
    employment_type_score: Mapped[int] = mapped_column(default=0, nullable=True)
    semantic_score: Mapped[int] = mapped_column(default=0, nullable=True)
    matched_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    missing_required: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    missing_preferred: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    transferable_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    suggested_skills: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    recommendation: Mapped[str] = mapped_column(String(30), nullable=False)
    strength_level: Mapped[str] = mapped_column(String(20), nullable=False)
    match_version: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_s2j_match_user_job"),
        Index("ix_s2j_match_user_score", "user_id", "overall_score"),
    )


class Skill2JobSkillGap(Base, UUIDMixin, TimestampMixin):
    """Persisted per-(candidate, job) skill-gap analysis (Phase 6).

    ``analysis`` mirrors the gap agent's deterministic output so every
    recommendation stays auditable and derived from engine inputs.
    """

    __tablename__ = "skill2job_skill_gaps"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("skill2job_jobs.id", ondelete="CASCADE"), nullable=False,
    )
    analysis: Mapped[dict] = mapped_column(JSON, nullable=False)
    analysis_version: Mapped[str] = mapped_column(String(50), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "job_id", name="uq_s2j_gap_user_job"),
        Index("ix_s2j_gap_user", "user_id"),
    )


class Skill2JobSimulation(Base, UUIDMixin, TimestampMixin):
    """Opportunity Unlock what-if simulation lockups.

    ``result`` mirrors the Matching Agent output so simulations are snapshot,
    diffable, and auditable.
    """

    __tablename__ = "skill2job_simulations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    dream_job_title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    skills_added: Mapped[list] = mapped_column(JSON, default=list, nullable=True)
    result: Mapped[dict] = mapped_column(JSON, nullable=False)


class Skill2JobTrainingProgress(Base, UUIDMixin, TimestampMixin):
    """Candidate training progress for a learning module (Phase 8 + Phase 3).

    Modules are grounded recommendations (real provider resources); completion
    is recorded by the candidate, never assumed by the system.

    Phase 3 additions:
    - evidence_state: tracks the 7-state learning progress progression
      (not_started → in_progress → completed → practiced → assessed → demonstrated → verified)
    - learning_hours: cumulative hours spent on this module
    """

    __tablename__ = "skill2job_training_progress"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    module_key: Mapped[str] = mapped_column(String(255), nullable=False)
    skill: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    provider: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str | None] = mapped_column(String(600), nullable=True)
    resource_type: Mapped[str] = mapped_column(String(30), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="in_progress", nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Phase 3: Evidence-aware learning progress
    evidence_state: Mapped[str] = mapped_column(
        String(30), default="not_started", nullable=False,
        comment="7-state progression: not_started, in_progress, completed, practiced, assessed, demonstrated, verified",
    )
    learning_hours: Mapped[float] = mapped_column(nullable=True, default=0.0)

    __table_args__ = (
        UniqueConstraint("user_id", "module_key", name="uq_s2j_training_user_module"),
        Index("ix_s2j_training_user", "user_id"),
    )


class Skill2JobExecutionTrace(Base, UUIDMixin, TimestampMixin):
    """LangGraph run trace metadata (Phase 8 + debugging/audit)."""

    __tablename__ = "skill2job_execution_traces"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    trace: Mapped[dict] = mapped_column(JSON, default=dict, nullable=True)