"""RankingImpactAnalyzer — Phase 4 Ranking Impact Analysis Engine.

Consumes persisted Phase 3 results (SimulationResult, SimulationImpact,
SimulationExecution) and produces a structured, recruiter-friendly analysis
of how the hypothetical hiring configuration changed candidate rankings.

Architecture:
    Phase 3: Candidate Pool -> Baseline Evaluation -> Simulation Evaluation
             -> Persist Candidate Results
    Phase 4: Persisted Candidate Results -> Impact Analyzer -> Ranking Impact
             Metrics -> Persisted/Computed Analysis -> Frontend Dashboard

This service is READ-ONLY with respect to production hiring data.
It never modifies JobDescription, CandidateRanking, Candidate, or Resume rows.

All calculations are deterministic and derived from actual simulation results.
"""

from __future__ import annotations

import statistics
import uuid
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.enums import SimulationStatus
from app.domain.models import User
from app.domain.simulation_models import (
    SimulationExecution,
    SimulationResult,
    SimulationScenario,
)
from app.domain.ranking_impact_schemas import (
    CandidateImpactDetail,
    CandidateImpactListResponse,
    CandidateSingleImpactResponse,
    InsightCard,
    MovementCategorySummary,
    QualificationMatrix,
    RankBucket,
    RankDistribution,
    RankMovement,
    RankStability,
    RankingImpactResponse,
    RankingOverview,
    ScoreBucket,
    ScoreDistribution,
    ScoreMovement,
    ShortlistImpact,
    ThresholdImpact,
    TopMover,
)
from app.repositories.simulation import SimulationRepository
from app.repositories.simulation_execution import (
    SimulationExecutionRepository,
    SimulationResultRepository,
)
from app.services.simulation.execution_service import SimulationExecutionService

logger = get_logger(__name__)

# ─── Configurable Thresholds ───────────────────────────────────────

# Movement category thresholds (centralized, not scattered as magic numbers)
SIGNIFICANT_IMPROVEMENT_THRESHOLD = 10
IMPROVEMENT_THRESHOLD = 3
DECLINE_THRESHOLD = -3
SIGNIFICANT_DECLINE_THRESHOLD = -10

# Default top movers limit
DEFAULT_TOP_MOVERS_LIMIT = 5

# Rank bucket boundaries (1-indexed, inclusive)
DEFAULT_RANK_BUCKETS: list[tuple[str, int, int | None]] = [
    ("1-5", 1, 5),
    ("6-10", 6, 10),
    ("11-20", 11, 20),
    ("21-50", 21, 50),
    ("51+", 51, None),
]

# Score band boundaries (0-100)
DEFAULT_SCORE_BANDS: list[tuple[str, int, int]] = [
    ("0-49", 0, 49),
    ("50-59", 50, 59),
    ("60-69", 60, 69),
    ("70-79", 70, 79),
    ("80-89", 80, 89),
    ("90-100", 90, 100),
]

_QUALIFIED = "qualified"
_NOT_QUALIFIED = "not_qualified"


def _safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """Safe division that returns default when denominator is zero."""
    if denominator == 0:
        return default
    return numerator / denominator


def _safe_percentage(part: int, total: int) -> float:
    """Safe percentage calculation."""
    return round(_safe_divide(part, total) * 100, 1)


def _calculate_median(values: list[int]) -> float:
    """Calculate median of a list of integers, returning 0.0 for empty lists."""
    if not values:
        return 0.0
    return float(statistics.median(values))


def _calculate_mean(values: list[int]) -> float:
    """Calculate mean of a list of integers."""
    if not values:
        return 0.0
    return round(statistics.mean(values), 2)


def _spearman_rank_correlation(
    ranks_a: list[int], ranks_b: list[int],
) -> float | None:
    """Calculate Spearman rank correlation between two rank lists.

    Returns None if there are fewer than 2 candidates or all ranks are
    identical (no variance to correlate).
    """
    n = len(ranks_a)
    if n < 2:
        return None

    # Check if all ranks are identical (no variance)
    if len(set(ranks_a)) == 1 or len(set(ranks_b)) == 1:
        return None

    # Using the simplified Spearman formula: rho = 1 - (6 * sum(d^2)) / (n * (n^2 - 1))
    # This works when there are no tied ranks. For tied ranks, this is an
    # approximation that remains useful for the purpose of this analytical tool.
    sum_d_squared = sum((a - b) ** 2 for a, b in zip(ranks_a, ranks_b))
    rho = 1.0 - (6.0 * sum_d_squared) / (n * (n * n - 1))
    return round(rho, 4)


@dataclass
class _AnalysisConfig:
    """Internal configuration for the analysis."""

    top_movers_limit: int = DEFAULT_TOP_MOVERS_LIMIT
    rank_buckets: list[tuple[str, int, int | None]] = field(
        default_factory=lambda: list(DEFAULT_RANK_BUCKETS),
    )
    score_bands: list[tuple[str, int, int]] = field(
        default_factory=lambda: list(DEFAULT_SCORE_BANDS),
    )


class RankingImpactAnalyzer:
    """Analyzes ranking impact from persisted Phase 3 simulation results.

    This is a READ-ONLY analyzer. It consumes SimulationResult rows
    produced by Phase 3 and computes structured ranking impact metrics.
    It never writes to live hiring tables.
    """

    def __init__(
        self,
        session: AsyncSession,
        execution_repo: SimulationExecutionRepository | None = None,
        result_repo: SimulationResultRepository | None = None,
        scenario_repo: SimulationRepository | None = None,
    ) -> None:
        self._session = session
        self._exec_repo = execution_repo or SimulationExecutionRepository(session)
        self._result_repo = result_repo or SimulationResultRepository(session)
        self._scenario_repo = scenario_repo or SimulationRepository(session)

    async def analyze(
        self,
        simulation_id: uuid.UUID,
        execution_id: uuid.UUID | None = None,
        config: _AnalysisConfig | None = None,
    ) -> RankingImpactResponse:
        """Run the full ranking impact analysis for a simulation execution.

        Args:
            simulation_id: The simulation scenario ID.
            execution_id: Optional specific execution ID. If None, uses
                         the latest completed execution.
            config: Optional analysis configuration overrides.

        Returns:
            Complete ranking impact analysis response.

        Raises:
            NotFoundError: If simulation or execution not found.
            ValidationError: If execution is not completed.
        """
        cfg = config or _AnalysisConfig()

        # Load scenario
        scenario = await self._scenario_repo.get(simulation_id)
        if not scenario:
            raise NotFoundError("Simulation not found")

        # Resolve execution
        execution = await self._resolve_execution(scenario, execution_id)

        # Load all results for this execution
        results = await self._result_repo.list_by_execution(execution.id)

        if not results:
            return self._empty_response(scenario, execution)

        # Extract configurations from snapshot
        snapshot = execution.configuration_snapshot or {}
        baseline_config = snapshot.get("baseline") or {}
        simulation_config = snapshot.get("simulation") or {}

        # Build all analysis sections
        overview = self._analyze_overview(results)
        score_movement = self._analyze_score_movement(results)
        rank_movement = self._analyze_rank_movement(results)
        top_upward = self._top_movers(results, direction="up", limit=cfg.top_movers_limit)
        top_downward = self._top_movers(results, direction="down", limit=cfg.top_movers_limit)
        shortlist_impact = self._analyze_shortlist_impact(results)
        qualification_matrix = self._analyze_qualification_matrix(results)
        rank_distribution = self._analyze_rank_distribution(results, cfg.rank_buckets)
        score_distribution = self._analyze_score_distribution(results, cfg.score_bands)
        threshold_impact = self._analyze_threshold_impact(
            results, baseline_config, simulation_config,
        )
        rank_stability = self._analyze_rank_stability(results)
        movement_categories = self._analyze_movement_categories(results)
        insights = self._generate_insights(
            overview, shortlist_impact, qualification_matrix,
            rank_stability, score_movement, movement_categories,
        )

        return RankingImpactResponse(
            simulation_id=simulation_id,
            execution_id=execution.id,
            execution_status=execution.status,
            scenario_name=scenario.name,
            job_title=scenario.job.title if scenario.job else "",
            company=scenario.job.company if scenario.job else "",
            engine_version=execution.engine_version,
            completed_at=execution.completed_at,
            overview=overview,
            score_movement=score_movement,
            rank_movement=rank_movement,
            shortlist_impact=shortlist_impact,
            qualification_matrix=qualification_matrix,
            rank_distribution=rank_distribution,
            score_distribution=score_distribution,
            threshold_impact=threshold_impact,
            rank_stability=rank_stability,
            top_upward_movers=top_upward,
            top_downward_movers=top_downward,
            movement_categories=movement_categories,
            insights=insights,
        )

    async def get_candidate_impact_list(
        self,
        simulation_id: uuid.UUID,
        execution_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        movement: str | None = None,
        shortlist_filter: str | None = None,
        qualification_filter: str | None = None,
        sort_by: str = "simulation_rank",
        order: str = "asc",
    ) -> CandidateImpactListResponse:
        """Get paginated candidate impact details with optional filtering."""
        scenario = await self._scenario_repo.get(simulation_id)
        if not scenario:
            raise NotFoundError("Simulation not found")

        execution = await self._resolve_execution(scenario, execution_id)
        items, total = await self._result_repo.paginated(
            execution.id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            order=order,
        )

        # Apply additional filters in Python (these are post-query filters
        # on movement/shortlist/qualification categories)
        candidates = [self._build_candidate_detail(r) for r in items]

        if movement:
            candidates = [c for c in candidates if c.movement_category == movement]
            total = len(candidates)
        if shortlist_filter:
            candidates = [c for c in candidates if c.shortlist_change == shortlist_filter]
            total = len(candidates)
        if qualification_filter:
            candidates = [c for c in candidates if c.qualification_change == qualification_filter]
            total = len(candidates)

        return CandidateImpactListResponse(
            simulation_id=simulation_id,
            execution_id=execution.id,
            total=total,
            page=page,
            page_size=page_size,
            items=candidates,
        )

    async def get_candidate_single_impact(
        self,
        simulation_id: uuid.UUID,
        candidate_id: uuid.UUID,
        execution_id: uuid.UUID | None = None,
    ) -> CandidateSingleImpactResponse:
        """Get detailed impact for a single candidate."""
        scenario = await self._scenario_repo.get(simulation_id)
        if not scenario:
            raise NotFoundError("Simulation not found")

        execution = await self._resolve_execution(scenario, execution_id)

        # Find the specific candidate result
        results = await self._result_repo.list_by_execution(execution.id)
        result = next((r for r in results if r.candidate_id == candidate_id), None)
        if not result:
            raise NotFoundError("Candidate result not found for this execution")

        detail = self._build_candidate_detail(result)

        baseline = {
            "score": result.baseline_score,
            "rank": result.baseline_rank,
            "status": result.baseline_status,
            "shortlisted": result.baseline_shortlisted,
            "dimensions": result.baseline_dimensions or {},
        }
        simulation = {
            "score": result.simulation_score,
            "rank": result.simulation_rank,
            "status": result.simulation_status,
            "shortlisted": result.simulation_shortlisted,
            "dimensions": result.simulation_dimensions or {},
        }
        changes = {
            "score_change": result.score_change,
            "rank_change": result.rank_change,
            "qualification_change": detail.qualification_change,
            "shortlist_change": detail.shortlist_change,
        }
        explanation = self._build_candidate_explanation(result, detail)

        return CandidateSingleImpactResponse(
            simulation_id=simulation_id,
            execution_id=execution.id,
            candidate=detail,
            baseline=baseline,
            simulation=simulation,
            changes=changes,
            explanation=explanation,
        )

    # ─── Private Analysis Methods ───────────────────────────────────

    async def _resolve_execution(
        self,
        scenario: SimulationScenario,
        execution_id: uuid.UUID | None,
    ) -> SimulationExecution:
        """Resolve execution: explicit ID or latest completed."""
        if execution_id is not None:
            execution = await self._exec_repo.get_for_scenario(scenario.id, execution_id)
            if not execution:
                raise NotFoundError("Execution not found")
            return execution
        execution = await self._exec_repo.latest_completed(scenario.id)
        if not execution:
            raise ValidationError(
                "No completed execution found. Run the simulation first.",
            )
        return execution

    def _empty_response(
        self,
        scenario: SimulationScenario,
        execution: SimulationExecution,
    ) -> RankingImpactResponse:
        """Return a valid but empty analysis when no results exist."""
        return RankingImpactResponse(
            simulation_id=scenario.id,
            execution_id=execution.id,
            execution_status=execution.status,
            scenario_name=scenario.name,
            job_title=scenario.job.title if scenario.job else "",
            company=scenario.job.company if scenario.job else "",
            engine_version=execution.engine_version,
            completed_at=execution.completed_at,
            overview=RankingOverview(
                total_candidates=0,
                average_score_change=0.0,
                median_score_change=0.0,
                average_rank_change=0.0,
                median_rank_change=0.0,
                candidates_moved_up=0,
                candidates_moved_down=0,
                candidates_unchanged=0,
                percentage_moved_up=0.0,
                percentage_moved_down=0.0,
                percentage_unchanged=0.0,
                largest_upward_movement=0,
                largest_downward_movement=0,
            ),
            score_movement=ScoreMovement(
                average_change=0.0,
                median_change=0.0,
                minimum_change=0,
                maximum_change=0,
                positive_change_count=0,
                negative_change_count=0,
                unchanged_count=0,
                positive_change_percentage=0.0,
                negative_change_percentage=0.0,
                unchanged_percentage=0.0,
            ),
            rank_movement=RankMovement(
                average_change=0.0,
                median_change=0.0,
                largest_upward_movement=0,
                largest_downward_movement=0,
                candidates_moving_up=0,
                candidates_moving_down=0,
                candidates_unchanged=0,
                percentage_moving_up=0.0,
                percentage_moving_down=0.0,
                percentage_unchanged=0.0,
            ),
            shortlist_impact=ShortlistImpact(
                baseline_size=0,
                simulation_size=0,
                candidates_entering=0,
                candidates_leaving=0,
                candidates_retained=0,
                overlap_count=0,
                jaccard_similarity=0.0,
                retention_rate=0.0,
                turnover_rate=0.0,
                expansion_count=0,
                expansion_description="No shortlist change",
            ),
            qualification_matrix=QualificationMatrix(
                baseline_qualified_simulation_qualified=0,
                baseline_qualified_simulation_not_qualified=0,
                baseline_not_qualified_simulation_qualified=0,
                baseline_not_qualified_simulation_not_qualified=0,
                newly_qualified=0,
                newly_disqualified=0,
                remained_qualified=0,
                remained_unqualified=0,
                total_qualified_change=0,
            ),
            rank_distribution=RankDistribution(buckets=[]),
            score_distribution=ScoreDistribution(buckets=[]),
            threshold_impact=ThresholdImpact(
                baseline_threshold=0,
                simulation_threshold=0,
                baseline_qualified_count=0,
                simulation_qualified_count=0,
                qualified_change=0,
                description="No results to analyze",
            ),
            rank_stability=RankStability(
                rank_stability=0.0,
                rank_correlation=None,
                rank_correlation_method=None,
                meaningful_movement_count=0,
                meaningful_movement_percentage=0.0,
            ),
            top_upward_movers=[],
            top_downward_movers=[],
            movement_categories=[],
            insights=[],
        )

    def _analyze_overview(self, results: list[SimulationResult]) -> RankingOverview:
        """Compute high-level overview metrics."""
        total = len(results)
        score_changes = [r.score_change for r in results]
        rank_changes = [r.rank_change for r in results]

        moved_up = sum(1 for r in results if r.rank_change > 0)
        moved_down = sum(1 for r in results if r.rank_change < 0)
        unchanged = total - moved_up - moved_down

        return RankingOverview(
            total_candidates=total,
            average_score_change=_calculate_mean(score_changes),
            median_score_change=_calculate_median(score_changes),
            average_rank_change=_calculate_mean(rank_changes),
            median_rank_change=_calculate_median(rank_changes),
            candidates_moved_up=moved_up,
            candidates_moved_down=moved_down,
            candidates_unchanged=unchanged,
            percentage_moved_up=_safe_percentage(moved_up, total),
            percentage_moved_down=_safe_percentage(moved_down, total),
            percentage_unchanged=_safe_percentage(unchanged, total),
            largest_upward_movement=max(rank_changes) if rank_changes else 0,
            largest_downward_movement=min(rank_changes) if rank_changes else 0,
        )

    def _analyze_score_movement(self, results: list[SimulationResult]) -> ScoreMovement:
        """Compute aggregate score change statistics."""
        total = len(results)
        score_changes = [r.score_change for r in results]
        positive = sum(1 for c in score_changes if c > 0)
        negative = sum(1 for c in score_changes if c < 0)
        unchanged = total - positive - negative

        return ScoreMovement(
            average_change=_calculate_mean(score_changes),
            median_change=_calculate_median(score_changes),
            minimum_change=min(score_changes) if score_changes else 0,
            maximum_change=max(score_changes) if score_changes else 0,
            positive_change_count=positive,
            negative_change_count=negative,
            unchanged_count=unchanged,
            positive_change_percentage=_safe_percentage(positive, total),
            negative_change_percentage=_safe_percentage(negative, total),
            unchanged_percentage=_safe_percentage(unchanged, total),
        )

    def _analyze_rank_movement(self, results: list[SimulationResult]) -> RankMovement:
        """Compute aggregate rank change statistics."""
        total = len(results)
        rank_changes = [r.rank_change for r in results]
        moving_up = sum(1 for c in rank_changes if c > 0)
        moving_down = sum(1 for c in rank_changes if c < 0)
        unchanged = total - moving_up - moving_down

        return RankMovement(
            average_change=_calculate_mean(rank_changes),
            median_change=_calculate_median(rank_changes),
            largest_upward_movement=max(rank_changes) if rank_changes else 0,
            largest_downward_movement=min(rank_changes) if rank_changes else 0,
            candidates_moving_up=moving_up,
            candidates_moving_down=moving_down,
            candidates_unchanged=unchanged,
            percentage_moving_up=_safe_percentage(moving_up, total),
            percentage_moving_down=_safe_percentage(moving_down, total),
            percentage_unchanged=_safe_percentage(unchanged, total),
        )

    def _top_movers(
        self,
        results: list[SimulationResult],
        direction: str,
        limit: int,
    ) -> list[TopMover]:
        """Identify top movers in a given direction.

        Tie-breaking is deterministic: by rank_change, then candidate_name.
        """
        if direction == "up":
            candidates = [r for r in results if r.rank_change > 0]
            candidates.sort(key=lambda r: (-r.rank_change, r.candidate_name))
        else:
            candidates = [r for r in results if r.rank_change < 0]
            candidates.sort(key=lambda r: (r.rank_change, r.candidate_name))

        return [
            TopMover(
                candidate_id=r.candidate_id,
                candidate_name=r.candidate_name,
                baseline_rank=r.baseline_rank,
                simulation_rank=r.simulation_rank,
                rank_change=r.rank_change,
                baseline_score=r.baseline_score,
                simulation_score=r.simulation_score,
                score_change=r.score_change,
                baseline_status=r.baseline_status,
                simulation_status=r.simulation_status,
                shortlisted_change=self._shortlist_change_label(r),
                movement_category=self._classify_movement(r.rank_change),
            )
            for r in candidates[:limit]
        ]

    def _analyze_shortlist_impact(self, results: list[SimulationResult]) -> ShortlistImpact:
        """Analyze shortlist composition changes."""
        baseline_shortlisted = {r.candidate_id for r in results if r.baseline_shortlisted}
        simulation_shortlisted = {r.candidate_id for r in results if r.simulation_shortlisted}

        baseline_size = len(baseline_shortlisted)
        simulation_size = len(simulation_shortlisted)

        retained = baseline_shortlisted & simulation_shortlisted
        entering = simulation_shortlisted - baseline_shortlisted
        leaving = baseline_shortlisted - simulation_shortlisted

        overlap_count = len(retained)
        union_count = len(baseline_shortlisted | simulation_shortlisted)

        jaccard = _safe_divide(overlap_count, union_count, 0.0)
        retention = _safe_divide(overlap_count, baseline_size, 0.0)
        turnover = _safe_divide(
            len(entering) + len(leaving),
            baseline_size if baseline_size > 0 else 1,
            0.0,
        )
        expansion = simulation_size - baseline_size

        if expansion > 0:
            expansion_desc = f"Shortlist expanded by {expansion} candidate(s)"
        elif expansion < 0:
            expansion_desc = f"Shortlist contracted by {abs(expansion)} candidate(s)"
        else:
            expansion_desc = "Shortlist size unchanged"

        return ShortlistImpact(
            baseline_size=baseline_size,
            simulation_size=simulation_size,
            candidates_entering=len(entering),
            candidates_leaving=len(leaving),
            candidates_retained=overlap_count,
            overlap_count=overlap_count,
            jaccard_similarity=round(jaccard, 4),
            retention_rate=round(retention, 4),
            turnover_rate=round(turnover, 4),
            expansion_count=expansion,
            expansion_description=expansion_desc,
        )

    def _analyze_qualification_matrix(
        self, results: list[SimulationResult],
    ) -> QualificationMatrix:
        """Build the qualification conversion matrix."""
        a = sum(
            1 for r in results
            if r.baseline_status == _QUALIFIED and r.simulation_status == _QUALIFIED
        )
        b = sum(
            1 for r in results
            if r.baseline_status == _QUALIFIED and r.simulation_status == _NOT_QUALIFIED
        )
        c = sum(
            1 for r in results
            if r.baseline_status == _NOT_QUALIFIED and r.simulation_status == _QUALIFIED
        )
        d = sum(
            1 for r in results
            if r.baseline_status == _NOT_QUALIFIED and r.simulation_status == _NOT_QUALIFIED
        )

        return QualificationMatrix(
            baseline_qualified_simulation_qualified=a,
            baseline_qualified_simulation_not_qualified=b,
            baseline_not_qualified_simulation_qualified=c,
            baseline_not_qualified_simulation_not_qualified=d,
            newly_qualified=c,
            newly_disqualified=b,
            remained_qualified=a,
            remained_unqualified=d,
            total_qualified_change=c - b,
        )

    def _analyze_rank_distribution(
        self,
        results: list[SimulationResult],
        buckets: list[tuple[str, int, int | None]],
    ) -> RankDistribution:
        """Analyze rank distribution across configurable buckets."""
        bucket_results: list[RankBucket] = []
        for label, lower, upper in buckets:
            baseline_count = sum(
                1 for r in results
                if r.baseline_rank >= lower and (upper is None or r.baseline_rank <= upper)
            )
            simulation_count = sum(
                1 for r in results
                if r.simulation_rank >= lower and (upper is None or r.simulation_rank <= upper)
            )
            bucket_results.append(
                RankBucket(
                    label=label,
                    lower_bound=lower,
                    upper_bound=upper,
                    baseline_count=baseline_count,
                    simulation_count=simulation_count,
                    change=simulation_count - baseline_count,
                )
            )
        return RankDistribution(buckets=bucket_results)

    def _analyze_score_distribution(
        self,
        results: list[SimulationResult],
        bands: list[tuple[str, int, int]],
    ) -> ScoreDistribution:
        """Analyze score distribution across configurable bands."""
        band_results: list[ScoreBucket] = []
        for label, lower, upper in bands:
            baseline_count = sum(
                1 for r in results
                if lower <= r.baseline_score <= upper
            )
            simulation_count = sum(
                1 for r in results
                if lower <= r.simulation_score <= upper
            )
            band_results.append(
                ScoreBucket(
                    label=label,
                    lower_bound=lower,
                    upper_bound=upper,
                    baseline_count=baseline_count,
                    simulation_count=simulation_count,
                    change=simulation_count - baseline_count,
                )
            )
        return ScoreDistribution(buckets=band_results)

    def _analyze_threshold_impact(
        self,
        results: list[SimulationResult],
        baseline_config: dict,
        simulation_config: dict,
    ) -> ThresholdImpact:
        """Analyze how threshold changes affect qualification counts."""
        baseline_threshold = int(baseline_config.get("threshold", 70))
        simulation_threshold = int(simulation_config.get("threshold", 70))

        baseline_qualified = sum(
            1 for r in results if r.baseline_status == _QUALIFIED
        )
        simulation_qualified = sum(
            1 for r in results if r.simulation_status == _QUALIFIED
        )
        change = simulation_qualified - baseline_qualified

        if change > 0:
            desc = f"{change} more candidates meet the simulated threshold"
        elif change < 0:
            desc = f"{abs(change)} fewer candidates meet the simulated threshold"
        else:
            desc = "Same number of candidates meet both thresholds"

        return ThresholdImpact(
            baseline_threshold=baseline_threshold,
            simulation_threshold=simulation_threshold,
            baseline_qualified_count=baseline_qualified,
            simulation_qualified_count=simulation_qualified,
            qualified_change=change,
            description=desc,
        )

    def _analyze_rank_stability(
        self, results: list[SimulationResult],
    ) -> RankStability:
        """Calculate neutral ranking stability metrics."""
        total = len(results)
        unchanged = sum(1 for r in results if r.rank_change == 0)
        stability = round(_safe_divide(unchanged, total), 4)

        baseline_ranks = [r.baseline_rank for r in results]
        simulation_ranks = [r.simulation_rank for r in results]
        correlation = _spearman_rank_correlation(baseline_ranks, simulation_ranks)

        meaningful_threshold = 3
        meaningful = sum(
            1 for r in results
            if abs(r.rank_change) >= meaningful_threshold
        )

        return RankStability(
            rank_stability=stability,
            rank_correlation=correlation,
            rank_correlation_method="spearman" if correlation is not None else None,
            meaningful_movement_count=meaningful,
            meaningful_movement_percentage=_safe_percentage(meaningful, total),
        )

    def _analyze_movement_categories(
        self, results: list[SimulationResult],
    ) -> list[MovementCategorySummary]:
        """Classify candidates into deterministic movement categories."""
        categories: dict[str, int] = {
            "significantly_improved": 0,
            "improved": 0,
            "unchanged": 0,
            "declined": 0,
            "significantly_declined": 0,
        }
        for r in results:
            cat = self._classify_movement(r.rank_change)
            categories[cat] = categories.get(cat, 0) + 1

        total = len(results)
        return [
            MovementCategorySummary(
                category=cat,
                count=count,
                percentage=_safe_percentage(count, total),
            )
            for cat, count in categories.items()
        ]

    @staticmethod
    def _classify_movement(rank_change: int) -> str:
        """Classify a rank change into a movement category.

        Thresholds are centralized and configurable.
        """
        if rank_change >= SIGNIFICANT_IMPROVEMENT_THRESHOLD:
            return "significantly_improved"
        if rank_change >= IMPROVEMENT_THRESHOLD:
            return "improved"
        if rank_change <= SIGNIFICANT_DECLINE_THRESHOLD:
            return "significantly_declined"
        if rank_change <= DECLINE_THRESHOLD:
            return "declined"
        return "unchanged"

    @staticmethod
    def _shortlist_change_label(r: SimulationResult) -> str:
        """Determine the shortlist change label for a result."""
        if r.baseline_shortlisted and r.simulation_shortlisted:
            return "retained"
        if not r.baseline_shortlisted and r.simulation_shortlisted:
            return "entered"
        if r.baseline_shortlisted and not r.simulation_shortlisted:
            return "left"
        return "unchanged"

    @staticmethod
    def _qualification_change_label(r: SimulationResult) -> str:
        """Determine the qualification change label for a result."""
        if r.baseline_status == _QUALIFIED and r.simulation_status == _QUALIFIED:
            return "remained_qualified"
        if r.baseline_status == _NOT_QUALIFIED and r.simulation_status == _QUALIFIED:
            return "newly_qualified"
        if r.baseline_status == _QUALIFIED and r.simulation_status == _NOT_QUALIFIED:
            return "newly_disqualified"
        return "remained_unqualified"

    def _build_candidate_detail(self, r: SimulationResult) -> CandidateImpactDetail:
        """Build a CandidateImpactDetail from a SimulationResult."""
        return CandidateImpactDetail(
            candidate_id=r.candidate_id,
            candidate_name=r.candidate_name,
            baseline_score=r.baseline_score,
            simulation_score=r.simulation_score,
            score_change=r.score_change,
            baseline_rank=r.baseline_rank,
            simulation_rank=r.simulation_rank,
            rank_change=r.rank_change,
            baseline_status=r.baseline_status,
            simulation_status=r.simulation_status,
            baseline_shortlisted=r.baseline_shortlisted,
            simulation_shortlisted=r.simulation_shortlisted,
            movement_category=self._classify_movement(r.rank_change),
            shortlist_change=self._shortlist_change_label(r),
            qualification_change=self._qualification_change_label(r),
            reason=r.reason,
        )

    @staticmethod
    def _build_candidate_explanation(
        r: SimulationResult, detail: CandidateImpactDetail,
    ) -> str:
        """Build a factual explanation for a single candidate's impact."""
        parts: list[str] = []

        parts.append(
            f"Rank changed from #{r.baseline_rank} to #{r.simulation_rank} "
            f"({r.rank_change:+d})."
        )
        parts.append(
            f"Score changed by {r.score_change:+d} points "
            f"({r.baseline_score} -> {r.simulation_score})."
        )

        if detail.shortlist_change == "entered":
            parts.append("Candidate entered the simulated shortlist.")
        elif detail.shortlist_change == "left":
            parts.append("Candidate left the simulated shortlist.")
        elif detail.shortlist_change == "retained":
            parts.append("Candidate remained in the simulated shortlist.")

        if detail.qualification_change == "newly_qualified":
            parts.append("Candidate now qualifies under the simulated threshold.")
        elif detail.qualification_change == "newly_disqualified":
            parts.append("Candidate no longer qualifies under the simulated threshold.")

        if r.reason:
            parts.append(f"Analysis: {r.reason}")

        return " ".join(parts)

    def _generate_insights(
        self,
        overview: RankingOverview,
        shortlist: ShortlistImpact,
        qualification: QualificationMatrix,
        stability: RankStability,
        score_movement: ScoreMovement,
        movement_cats: list[MovementCategorySummary],
    ) -> list[InsightCard]:
        """Generate deterministic factual insights from computed metrics.

        These are observational statements, NOT evaluative recommendations.
        """
        insights: list[InsightCard] = []

        if overview.candidates_moved_up > 0:
            insights.append(InsightCard(
                type="movement",
                message=f"{overview.candidates_moved_up} candidate(s) moved upward in the simulated ranking.",
                metric_value=overview.candidates_moved_up,
                metric_unit="candidates",
            ))

        if overview.candidates_moved_down > 0:
            insights.append(InsightCard(
                type="movement",
                message=f"{overview.candidates_moved_down} candidate(s) moved downward in the simulated ranking.",
                metric_value=overview.candidates_moved_down,
                metric_unit="candidates",
            ))

        if shortlist.candidates_entering > 0:
            insights.append(InsightCard(
                type="shortlist",
                message=f"{shortlist.candidates_entering} candidate(s) entered the simulated shortlist.",
                metric_value=shortlist.candidates_entering,
                metric_unit="candidates",
            ))

        if shortlist.candidates_leaving > 0:
            insights.append(InsightCard(
                type="shortlist",
                message=f"{shortlist.candidates_leaving} candidate(s) left the baseline shortlist.",
                metric_value=shortlist.candidates_leaving,
                metric_unit="candidates",
            ))

        if shortlist.baseline_size > 0:
            retention_pct = round(shortlist.retention_rate * 100, 1)
            insights.append(InsightCard(
                type="shortlist",
                message=(
                    f"The simulated shortlist retains {retention_pct}% "
                    f"of the baseline shortlist."
                ),
                metric_value=retention_pct,
                metric_unit="percent",
            ))

        if qualification.newly_qualified > 0:
            insights.append(InsightCard(
                type="qualification",
                message=f"{qualification.newly_qualified} candidate(s) changed from not qualified to qualified.",
                metric_value=qualification.newly_qualified,
                metric_unit="candidates",
            ))

        if qualification.newly_disqualified > 0:
            insights.append(InsightCard(
                type="qualification",
                message=f"{qualification.newly_disqualified} candidate(s) changed from qualified to not qualified.",
                metric_value=qualification.newly_disqualified,
                metric_unit="candidates",
            ))

        if stability.rank_correlation is not None:
            insights.append(InsightCard(
                type="stability",
                message=f"Spearman rank correlation: {stability.rank_correlation:.4f}",
                metric_value=stability.rank_correlation,
                metric_unit="correlation",
            ))

        if score_movement.positive_change_count > 0 and score_movement.negative_change_count > 0:
            insights.append(InsightCard(
                type="distribution",
                message=(
                    f"Score changes: {score_movement.positive_change_count} improved, "
                    f"{score_movement.negative_change_count} declined, "
                    f"{score_movement.unchanged_count} unchanged."
                ),
            ))

        return insights
