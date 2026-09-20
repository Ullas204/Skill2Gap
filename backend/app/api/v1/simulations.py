"""Simulation scenario management API (Phase 1) and execution API (Phase 3).

Phase 1 provides CRUD for hiring-simulation scenarios. Phase 3 adds the real
"what-if" run endpoint (``POST /{id}/run``) plus the execution/results/summary
queries used by the results page. Multi-tenant isolation is enforced inside the
service layer, never by the client.
"""

import logging
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.core.logging import get_logger
from app.db.session import get_db
from app.domain.enums import AuditEventType
from app.domain.models import User
from app.domain.ranking_impact_schemas import (
    CandidateImpactListResponse,
    CandidateSingleImpactResponse,
    RankingImpactResponse,
)
from app.domain.requirement_impact_schemas import (
    CandidateRequirementImpactDetailResponse,
    CandidateRequirementImpactListResponse,
    RequirementImpactListResponse,
    RequirementImpactResponse,
)
from app.domain.simulation_schemas import (
    SimulationChangesResponse,
    SimulationExecutionListResponse,
    SimulationExecutionResponse,
    SimulationResultsResponse,
    SimulationScenarioCreate,
    SimulationScenarioListResponse,
    SimulationScenarioResponse,
    SimulationScenarioUpdate,
    SimulationStatusResponse,
    SimulationSummaryResponse,
    SimulationValidationResponse,
)
from app.services.audit_service import AuditService
from app.services.simulation.execution_service import SimulationExecutionService
from app.services.simulation.ranking_impact_analyzer import RankingImpactAnalyzer
from app.services.simulation.requirement_impact_analyzer import RequirementImpactAnalyzer
from app.services.simulation.scheduler import _celery_available, queue_simulation_execution
from app.services.simulation.simulation_service import SimulationScenarioService

logger = get_logger(__name__)

router = APIRouter(prefix="/simulations", tags=["simulations"])


def _get_service(db: AsyncSession = Depends(get_db)) -> SimulationScenarioService:
    return SimulationScenarioService(db)


def _get_execution_service(db: AsyncSession = Depends(get_db)) -> SimulationExecutionService:
    return SimulationExecutionService(db)


def _get_ranking_impact_analyzer(db: AsyncSession = Depends(get_db)) -> RankingImpactAnalyzer:
    return RankingImpactAnalyzer(db)


def _get_requirement_impact_analyzer(db: AsyncSession = Depends(get_db)) -> RequirementImpactAnalyzer:
    return RequirementImpactAnalyzer(db)


@router.post("", response_model=SimulationScenarioResponse, status_code=201)
async def create_simulation(
    body: SimulationScenarioCreate,
    service: SimulationScenarioService = Depends(_get_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    return await service.create_scenario(current_user, body)


@router.get("", response_model=SimulationScenarioListResponse)
async def list_simulations(
    service: SimulationScenarioService = Depends(_get_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    return await service.list_scenarios(current_user)


@router.get("/{simulation_id}", response_model=SimulationScenarioResponse)
async def get_simulation(
    simulation_id: uuid.UUID,
    service: SimulationScenarioService = Depends(_get_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    return await service.get_scenario(current_user, simulation_id)


@router.get("/{simulation_id}/status", response_model=SimulationStatusResponse)
async def get_simulation_status(
    simulation_id: uuid.UUID,
    service: SimulationScenarioService = Depends(_get_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    return await service.get_status(current_user, simulation_id)


@router.patch("/{simulation_id}", response_model=SimulationScenarioResponse)
async def update_simulation(
    simulation_id: uuid.UUID,
    body: SimulationScenarioUpdate,
    service: SimulationScenarioService = Depends(_get_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    return await service.update_scenario(current_user, simulation_id, body)


@router.post("/{simulation_id}/validate", response_model=SimulationValidationResponse)
async def validate_simulation(
    simulation_id: uuid.UUID,
    service: SimulationScenarioService = Depends(_get_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Validate the current configuration. Read-only; returns structured errors."""
    return await service.validate_scenario(current_user, simulation_id)


@router.get("/{simulation_id}/changes", response_model=SimulationChangesResponse)
async def get_simulation_changes(
    simulation_id: uuid.UUID,
    service: SimulationScenarioService = Depends(_get_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Baseline-vs-scenario diff for the Scenario Builder review section."""
    return await service.get_scenario_changes(current_user, simulation_id)


@router.delete("/{simulation_id}", status_code=204)
async def delete_simulation(
    simulation_id: uuid.UUID,
    service: SimulationScenarioService = Depends(_get_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    await service.delete_scenario(current_user, simulation_id)
    return None


# ─── Phase 3: execution engine ───────────────────────────────────────


@router.post("/{simulation_id}/run", response_model=SimulationExecutionResponse, status_code=202)
async def run_simulation(
    simulation_id: uuid.UUID,
    service: SimulationExecutionService = Depends(_get_execution_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Queue a real what-if run of the scenario against the live candidate pool.

    Dispatched to Celery when a broker is reachable; otherwise executed inline in
    the same request session (dev/test fallback) so the response reflects the
    actual outcome. The execution row always carries ``status``/``progress`` for
    the frontend's polling.
    """
    execution = await service.run_scenario(current_user, simulation_id)
    if _celery_available():
        dispatch = queue_simulation_execution(execution.scenario_id, execution.id)
        if dispatch.get("status") == "queued":
            return execution
    logger.info(
        "Broker unavailable or dispatch failed — running simulation inline "
        "(scenario=%s execution=%s)",
        execution.scenario_id,
        execution.id,
    )
    await service.execute(execution.id)
    return await service.get_execution(current_user, simulation_id, execution.id)


@router.get("/{simulation_id}/executions", response_model=SimulationExecutionListResponse)
async def list_simulation_executions(
    simulation_id: uuid.UUID,
    service: SimulationExecutionService = Depends(_get_execution_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    return await service.list_executions(current_user, simulation_id)


@router.get("/{simulation_id}/executions/{execution_id}", response_model=SimulationExecutionResponse)
async def get_simulation_execution(
    simulation_id: uuid.UUID,
    execution_id: uuid.UUID,
    service: SimulationExecutionService = Depends(_get_execution_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    return await service.get_execution(current_user, simulation_id, execution_id)


@router.post(
    "/{simulation_id}/executions/{execution_id}/cancel",
    response_model=SimulationExecutionResponse,
)
async def cancel_simulation_execution(
    simulation_id: uuid.UUID,
    execution_id: uuid.UUID,
    service: SimulationExecutionService = Depends(_get_execution_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    return await service.cancel_execution(current_user, simulation_id, execution_id)


@router.get("/{simulation_id}/results", response_model=SimulationResultsResponse)
async def list_simulation_results(
    simulation_id: uuid.UUID,
    execution_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    sort_by: str = Query(default="simulation_rank"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    change_filter: str | None = Query(
        default=None,
        pattern="^(improved|declined|entered_shortlist|left_shortlist|qualified|disqualified)$",
    ),
    service: SimulationExecutionService = Depends(_get_execution_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Paginated baseline-vs-scenario results. Defaults to the latest completed
    execution when ``execution_id`` is omitted."""
    return await service.list_results(
        current_user,
        simulation_id,
        execution_id=execution_id,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        order=order,
        change_filter=change_filter,
    )


@router.get("/{simulation_id}/summary", response_model=SimulationSummaryResponse)
async def get_simulation_summary(
    simulation_id: uuid.UUID,
    execution_id: uuid.UUID | None = Query(default=None),
    service: SimulationExecutionService = Depends(_get_execution_service),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Aggregate impact + major movers. Defaults to the latest completed
    execution when ``execution_id`` is omitted."""
    return await service.get_summary(current_user, simulation_id, execution_id)


# ─── Phase 4: Ranking Impact Analysis ──────────────────────────────


@router.get("/{simulation_id}/ranking-impact", response_model=RankingImpactResponse)
async def get_ranking_impact(
    simulation_id: uuid.UUID,
    execution_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    analyzer: RankingImpactAnalyzer = Depends(_get_ranking_impact_analyzer),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Full ranking impact analysis. Defaults to the latest completed execution.

    Returns structured analysis of ranking movement, score movement, shortlist
    impact, qualification changes, rank/score distributions, top movers,
    rank stability, and factual insights — all derived from persisted
    Phase 3 simulation results.
    """
    # Enforce RBAC + tenant isolation via the scenario service
    scenario_service = SimulationScenarioService(db)
    scenario = await scenario_service._load_or_404(simulation_id)
    await scenario_service._require_view(current_user, scenario)

    result = await analyzer.analyze(simulation_id, execution_id=execution_id)

    # Best-effort audit log — don't fail the request if audit fails
    try:
        audit_svc = AuditService(db)
        await audit_svc.log(
            event_type=AuditEventType.RANKING_IMPACT_VIEWED,
            action="ranking_impact_viewed",
            user_id=current_user.id,
            resource_type="simulation_execution",
            resource_id=str(result.execution_id),
            details={"simulation_id": str(simulation_id)},
        )
    except Exception:
        pass

    return result


@router.get(
    "/{simulation_id}/ranking-impact/candidates",
    response_model=CandidateImpactListResponse,
)
async def get_ranking_impact_candidates(
    simulation_id: uuid.UUID,
    execution_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    movement: str | None = Query(
        default=None,
        pattern="^(significantly_improved|improved|unchanged|declined|significantly_declined)$",
    ),
    shortlist: str | None = Query(
        default=None,
        pattern="^(entered|left|retained|unchanged)$",
    ),
    qualification: str | None = Query(
        default=None,
        pattern="^(newly_qualified|newly_disqualified|remained_qualified|remained_unqualified)$",
    ),
    sort_by: str = Query(default="simulation_rank"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    analyzer: RankingImpactAnalyzer = Depends(_get_ranking_impact_analyzer),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Paginated candidate impact with optional movement/shortlist/qualification filters."""
    scenario_service = SimulationScenarioService(db)
    scenario = await scenario_service._load_or_404(simulation_id)
    await scenario_service._require_view(current_user, scenario)

    return await analyzer.get_candidate_impact_list(
        simulation_id,
        execution_id=execution_id,
        page=page,
        page_size=page_size,
        movement=movement,
        shortlist_filter=shortlist,
        qualification_filter=qualification,
        sort_by=sort_by,
        order=order,
    )


@router.get(
    "/{simulation_id}/ranking-impact/candidates/{candidate_id}",
    response_model=CandidateSingleImpactResponse,
)
async def get_candidate_impact_detail(
    simulation_id: uuid.UUID,
    candidate_id: uuid.UUID,
    execution_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    analyzer: RankingImpactAnalyzer = Depends(_get_ranking_impact_analyzer),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Detailed ranking impact for a single candidate."""
    scenario_service = SimulationScenarioService(db)
    scenario = await scenario_service._load_or_404(simulation_id)
    await scenario_service._require_view(current_user, scenario)

    return await analyzer.get_candidate_single_impact(
        simulation_id, candidate_id, execution_id=execution_id,
    )


# ─── Phase 5: Requirement Impact Analysis ─────────────────────────


@router.get("/{simulation_id}/requirement-impact", response_model=RequirementImpactResponse)
async def get_requirement_impact(
    simulation_id: uuid.UUID,
    execution_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    analyzer: RequirementImpactAnalyzer = Depends(_get_requirement_impact_analyzer),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Full requirement impact analysis. Defaults to the latest completed execution.

    Returns structured analysis of requirement changes, per-requirement impact,
    affected candidates, qualification changes, and score attribution — all
    derived from persisted Phase 3 simulation results and configuration snapshots.
    """
    scenario_service = SimulationScenarioService(db)
    scenario = await scenario_service._load_or_404(simulation_id)
    await scenario_service._require_view(current_user, scenario)

    result = await analyzer.analyze(simulation_id, execution_id=execution_id)

    try:
        audit_svc = AuditService(db)
        await audit_svc.log(
            event_type=AuditEventType.REQUIREMENT_IMPACT_VIEWED,
            action="requirement_impact_viewed",
            user_id=current_user.id,
            resource_type="simulation_execution",
            resource_id=str(result.execution_id),
            details={"simulation_id": str(simulation_id)},
        )
    except Exception:
        pass

    return result


@router.get(
    "/{simulation_id}/requirement-impact/requirements",
    response_model=RequirementImpactListResponse,
)
async def get_requirement_impact_requirements(
    simulation_id: uuid.UUID,
    execution_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    analyzer: RequirementImpactAnalyzer = Depends(_get_requirement_impact_analyzer),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Paginated list of changed requirements with impact metrics."""
    scenario_service = SimulationScenarioService(db)
    scenario = await scenario_service._load_or_404(simulation_id)
    await scenario_service._require_view(current_user, scenario)

    return await analyzer.get_requirement_list(
        simulation_id,
        execution_id=execution_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{simulation_id}/requirement-impact/candidates",
    response_model=CandidateRequirementImpactListResponse,
)
async def get_requirement_impact_candidates(
    simulation_id: uuid.UUID,
    execution_id: uuid.UUID | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    requirement: str | None = Query(default=None),
    requirement_type: str | None = Query(
        default=None,
        pattern="^(skill|experience|education)$",
    ),
    newly_qualified: bool | None = Query(default=None),
    newly_disqualified: bool | None = Query(default=None),
    sort_by: str = Query(default="simulation_rank"),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db),
    analyzer: RequirementImpactAnalyzer = Depends(_get_requirement_impact_analyzer),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Paginated candidate requirement impacts with optional filtering."""
    scenario_service = SimulationScenarioService(db)
    scenario = await scenario_service._load_or_404(simulation_id)
    await scenario_service._require_view(current_user, scenario)

    return await analyzer.get_affected_candidates(
        simulation_id,
        execution_id=execution_id,
        page=page,
        page_size=page_size,
        requirement=requirement,
        requirement_type=requirement_type,
        newly_qualified=newly_qualified,
        newly_disqualified=newly_disqualified,
        sort_by=sort_by,
        order=order,
    )


@router.get(
    "/{simulation_id}/requirement-impact/candidates/{candidate_id}",
    response_model=CandidateRequirementImpactDetailResponse,
)
async def get_candidate_requirement_impact_detail(
    simulation_id: uuid.UUID,
    candidate_id: uuid.UUID,
    execution_id: uuid.UUID | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    analyzer: RequirementImpactAnalyzer = Depends(_get_requirement_impact_analyzer),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
):
    """Detailed requirement impact for a single candidate."""
    scenario_service = SimulationScenarioService(db)
    scenario = await scenario_service._load_or_404(simulation_id)
    await scenario_service._require_view(current_user, scenario)

    return await analyzer.get_candidate_detail(
        simulation_id, candidate_id, execution_id=execution_id,
    )