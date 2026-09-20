"""Pydantic schemas for Phase 5 — What-If Requirement Impact Analysis.

These schemas define the structured API response for requirement impact
analysis. The analyzer consumes persisted Phase 3 results (SimulationResult,
SimulationExecution) and the configuration snapshots to decompose ranking
impact by individual requirement changes.

All values are derived from actual data — never hardcoded.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ─── Requirement Change Detail ─────────────────────────────────────


class ChangedRequirementStatus(BaseModel):
    """One requirement's satisfaction status change for a candidate."""

    requirement_type: str  # "skill" | "experience" | "education"
    requirement_name: str  # "Docker", "experience", "education"
    baseline_satisfied: bool
    simulation_satisfied: bool
    baseline_status: str  # "SATISFIED" | "MISSING" | "NOT_APPLICABLE"
    simulation_status: str  # "SATISFIED" | "MISSING" | "NOT_APPLICABLE"


class RequirementChangeDetail(BaseModel):
    """One changed requirement with its type, before/after values, and impact."""

    requirement_type: str  # "skill" | "experience" | "education"
    requirement_name: str  # "Docker", "experience", "education"
    change_type: str  # "added" | "removed" | "promoted" | "demoted" | "modified"
    baseline_value: str  # "preferred", "2+ years", "Bachelor's"
    simulation_value: str  # "mandatory", "4+ years", "Master's"
    affected_candidates: int = 0
    newly_disqualified: int = 0
    newly_qualified: int = 0
    avg_score_impact: float = 0.0
    impact_category: str = "NO_CANDIDATE_IMPACT"  # NO/LOW/MODERATE/HIGH


class CandidateRequirementImpact(BaseModel):
    """Per-candidate requirement satisfaction change with impact details."""

    candidate_id: uuid.UUID
    candidate_name: str
    affected_requirements: list[ChangedRequirementStatus] = Field(default_factory=list)
    baseline_score: int
    simulation_score: int
    score_change: int
    baseline_rank: int
    simulation_rank: int
    rank_change: int
    baseline_qualified: bool
    simulation_qualified: bool
    qualification_change: str  # "newly_qualified" | "newly_disqualified" | "remained_qualified" | "remained_unqualified"
    shortlist_change: str  # "entered" | "left" | "retained" | "never_shortlisted"


# ─── Summary Schemas ───────────────────────────────────────────────


class RequirementChangeSummary(BaseModel):
    """Aggregate summary of all requirement changes."""

    total_requirements_changed: int = 0
    skills_added: int = 0
    skills_removed: int = 0
    skills_promoted: int = 0  # preferred -> mandatory
    skills_demoted: int = 0  # mandatory -> preferred
    experience_changed: bool = False
    education_changed: bool = False


class RequirementImpactSummary(BaseModel):
    """Aggregate impact metrics across all changed requirements."""

    candidates_affected: int = 0
    candidates_newly_qualified: int = 0
    candidates_newly_disqualified: int = 0
    candidates_score_changed: int = 0
    candidates_rank_changed: int = 0
    candidates_shortlist_changed: int = 0


# ─── Main Response ─────────────────────────────────────────────────


class RequirementImpactResponse(BaseModel):
    """Complete requirement impact analysis response.

    This is the primary API response for GET /simulations/{id}/requirement-impact.
    All values are derived from persisted Phase 3 simulation results and
    configuration snapshots.
    """

    simulation_id: uuid.UUID
    execution_id: uuid.UUID
    execution_status: str
    scenario_name: str
    job_title: str
    company: str
    completed_at: datetime | None

    # Change summary
    change_summary: RequirementChangeSummary
    # Impact summary
    impact_summary: RequirementImpactSummary
    # Per-requirement changes
    requirement_changes: list[RequirementChangeDetail] = Field(default_factory=list)


# ─── Paginated Lists ───────────────────────────────────────────────


class RequirementImpactListResponse(BaseModel):
    """Paginated list of requirement change details."""

    simulation_id: uuid.UUID
    execution_id: uuid.UUID
    total: int
    page: int
    page_size: int
    items: list[RequirementChangeDetail] = Field(default_factory=list)


class CandidateRequirementImpactDetail(BaseModel):
    """Detailed candidate requirement impact for a single candidate."""

    candidate_id: uuid.UUID
    candidate_name: str
    baseline_score: int
    simulation_score: int
    score_change: int
    baseline_rank: int
    simulation_rank: int
    rank_change: int
    baseline_qualified: bool
    simulation_qualified: bool
    qualification_change: str
    shortlist_change: str
    affected_requirements: list[ChangedRequirementStatus] = Field(default_factory=list)
    explanation: str = ""


class CandidateRequirementImpactListResponse(BaseModel):
    """Paginated list of candidate requirement impacts with filtering."""

    simulation_id: uuid.UUID
    execution_id: uuid.UUID
    total: int
    page: int
    page_size: int
    items: list[CandidateRequirementImpactDetail] = Field(default_factory=list)


class CandidateRequirementImpactDetailResponse(BaseModel):
    """Full detail for a single candidate's requirement impact."""

    simulation_id: uuid.UUID
    execution_id: uuid.UUID
    candidate: CandidateRequirementImpactDetail
    baseline: dict
    simulation: dict
    changes: dict
    explanation: str
