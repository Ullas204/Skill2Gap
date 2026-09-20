"""Pydantic schemas for Phase 4 — Ranking Impact Analysis.

These schemas define the structured API response for ranking impact analysis.
The analyzer consumes persisted Phase 3 results (SimulationResult, SimulationImpact)
and produces a recruiter-friendly breakdown of ranking movement, shortlist changes,
qualification shifts, and distribution analysis.

All values are derived from actual data — never hardcoded.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ─── Candidate-Level Impact ────────────────────────────────────────


class CandidateImpactDetail(BaseModel):
    """Per-candidate ranking impact detail for the impact dashboard."""

    candidate_id: uuid.UUID
    candidate_name: str
    baseline_score: int
    simulation_score: int
    score_change: int
    baseline_rank: int
    simulation_rank: int
    rank_change: int
    baseline_status: str
    simulation_status: str
    baseline_shortlisted: bool
    simulation_shortlisted: bool
    movement_category: str
    shortlist_change: str  # "entered" | "left" | "retained" | "never_shortlisted"
    qualification_change: str  # "newly_qualified" | "newly_disqualified" | "remained_qualified" | "remained_unqualified"
    reason: str | None = None

    model_config = {"from_attributes": True}


# ─── Overview ──────────────────────────────────────────────────────


class RankingOverview(BaseModel):
    """High-level summary of the ranking impact analysis."""

    total_candidates: int
    average_score_change: float
    median_score_change: float
    average_rank_change: float
    median_rank_change: float
    candidates_moved_up: int
    candidates_moved_down: int
    candidates_unchanged: int
    percentage_moved_up: float
    percentage_moved_down: float
    percentage_unchanged: float
    largest_upward_movement: int
    largest_downward_movement: int


# ─── Score Movement ────────────────────────────────────────────────


class ScoreMovement(BaseModel):
    """Aggregate score change statistics."""

    average_change: float
    median_change: float
    minimum_change: int
    maximum_change: int
    positive_change_count: int
    negative_change_count: int
    unchanged_count: int
    positive_change_percentage: float
    negative_change_percentage: float
    unchanged_percentage: float


# ─── Rank Movement ─────────────────────────────────────────────────


class RankMovement(BaseModel):
    """Aggregate rank change statistics."""

    average_change: float
    median_change: float
    largest_upward_movement: int
    largest_downward_movement: int
    candidates_moving_up: int
    candidates_moving_down: int
    candidates_unchanged: int
    percentage_moving_up: float
    percentage_moving_down: float
    percentage_unchanged: float


# ─── Top Movers ────────────────────────────────────────────────────


class TopMover(BaseModel):
    """A candidate with significant ranking movement."""

    candidate_id: uuid.UUID
    candidate_name: str
    baseline_rank: int
    simulation_rank: int
    rank_change: int
    baseline_score: int
    simulation_score: int
    score_change: int
    baseline_status: str
    simulation_status: str
    shortlisted_change: str  # "entered" | "left" | "retained" | "unchanged"
    movement_category: str


# ─── Shortlist Impact ──────────────────────────────────────────────


class ShortlistImpact(BaseModel):
    """Shortlist composition changes between baseline and simulation."""

    baseline_size: int
    simulation_size: int
    candidates_entering: int
    candidates_leaving: int
    candidates_retained: int
    overlap_count: int
    jaccard_similarity: float
    retention_rate: float
    turnover_rate: float
    expansion_count: int  # positive means expansion, negative means contraction
    expansion_description: str


# ─── Qualification Impact ──────────────────────────────────────────


class QualificationMatrix(BaseModel):
    """Qualification conversion matrix (baseline x simulation)."""

    baseline_qualified_simulation_qualified: int
    baseline_qualified_simulation_not_qualified: int
    baseline_not_qualified_simulation_qualified: int
    baseline_not_qualified_simulation_not_qualified: int
    newly_qualified: int
    newly_disqualified: int
    remained_qualified: int
    remained_unqualified: int
    total_qualified_change: int


# ─── Rank Distribution ─────────────────────────────────────────────


class RankBucket(BaseModel):
    """Candidate count in a rank band for baseline and simulation."""

    label: str
    lower_bound: int
    upper_bound: int | None
    baseline_count: int
    simulation_count: int
    change: int


class RankDistribution(BaseModel):
    """Rank distribution across configurable buckets."""

    buckets: list[RankBucket]


# ─── Score Distribution ────────────────────────────────────────────


class ScoreBucket(BaseModel):
    """Candidate count in a score band for baseline and simulation."""

    label: str
    lower_bound: int
    upper_bound: int
    baseline_count: int
    simulation_count: int
    change: int


class ScoreDistribution(BaseModel):
    """Score distribution across configurable bands."""

    buckets: list[ScoreBucket]


# ─── Threshold Impact ──────────────────────────────────────────────


class ThresholdImpact(BaseModel):
    """Impact of the threshold change on qualification counts."""

    baseline_threshold: int
    simulation_threshold: int
    baseline_qualified_count: int
    simulation_qualified_count: int
    qualified_change: int
    description: str


# ─── Stability & Correlation ───────────────────────────────────────


class RankStability(BaseModel):
    """Neutral ranking stability metrics."""

    rank_stability: float  # unchanged_rank_candidates / total_candidates
    rank_correlation: float | None  # Spearman rho, None if insufficient data
    rank_correlation_method: str | None
    meaningful_movement_count: int
    meaningful_movement_percentage: float


# ─── Insight Cards ─────────────────────────────────────────────────


class InsightCard(BaseModel):
    """A factual, deterministic observation about the simulation impact."""

    type: str  # "movement" | "shortlist" | "qualification" | "distribution" | "stability"
    message: str
    metric_value: float | int | None = None
    metric_unit: str | None = None


# ─── Movement Category Summary ─────────────────────────────────────


class MovementCategorySummary(BaseModel):
    """Count of candidates in each movement category."""

    category: str
    count: int
    percentage: float


# ─── Main Response ─────────────────────────────────────────────────


class RankingImpactResponse(BaseModel):
    """Complete ranking impact analysis response.

    This is the primary API response for GET /simulations/{id}/ranking-impact.
    All values are derived from persisted Phase 3 simulation results.
    """

    simulation_id: uuid.UUID
    execution_id: uuid.UUID
    execution_status: str
    scenario_name: str
    job_title: str
    company: str
    engine_version: str
    completed_at: datetime | None

    overview: RankingOverview
    score_movement: ScoreMovement
    rank_movement: RankMovement
    shortlist_impact: ShortlistImpact
    qualification_matrix: QualificationMatrix
    rank_distribution: RankDistribution
    score_distribution: ScoreDistribution
    threshold_impact: ThresholdImpact
    rank_stability: RankStability
    top_upward_movers: list[TopMover]
    top_downward_movers: list[TopMover]
    movement_categories: list[MovementCategorySummary]
    insights: list[InsightCard]


# ─── Paginated Candidate Impact ────────────────────────────────────


class CandidateImpactListResponse(BaseModel):
    """Paginated list of candidate impact details with filtering."""

    simulation_id: uuid.UUID
    execution_id: uuid.UUID
    total: int
    page: int
    page_size: int
    items: list[CandidateImpactDetail] = Field(default_factory=list)


# ─── Single Candidate Impact ───────────────────────────────────────


class CandidateSingleImpactResponse(BaseModel):
    """Detailed impact for a single candidate."""

    simulation_id: uuid.UUID
    execution_id: uuid.UUID
    candidate: CandidateImpactDetail
    baseline: dict
    simulation: dict
    changes: dict
    explanation: str
