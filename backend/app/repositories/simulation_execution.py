"""Repository for Simulation Execution persistence (Phase 3).

The result filter/order logic lives here. Filtering is done on plain scalar
columns (scores, ranks, booleans) which work identically on SQLite (tests) and
Postgres (prod); the JSON dimension columns are never used in WHERE clauses.
"""

from __future__ import annotations

import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.simulation_models import (
    SimulationExecution,
    SimulationImpact,
    SimulationResult,
)
from app.repositories.base import BaseRepository

EXECUTION_STATUSES = {"queued", "running", "completed", "failed", "cancelled"}

ACTIVE_STATUSES = {"queued", "running"}

RESULT_CHANGE_FILTERS: dict[str, list] = {
    "improved": [SimulationResult.score_change > 0],
    "declined": [SimulationResult.score_change < 0],
    "entered_shortlist": [
        SimulationResult.simulation_shortlisted.is_(True),
        SimulationResult.baseline_shortlisted.is_(False),
    ],
    "left_shortlist": [
        SimulationResult.baseline_shortlisted.is_(True),
        SimulationResult.simulation_shortlisted.is_(False),
    ],
    "qualified": [SimulationResult.simulation_status == "qualified"],
    "disqualified": [SimulationResult.simulation_status == "not_qualified"],
}

RESULT_SORT_COLUMNS: dict[str, object] = {
    "candidate_name": SimulationResult.candidate_name,
    "baseline_score": SimulationResult.baseline_score,
    "simulation_score": SimulationResult.simulation_score,
    "score_change": SimulationResult.score_change,
    "baseline_rank": SimulationResult.baseline_rank,
    "simulation_rank": SimulationResult.simulation_rank,
    "rank_change": SimulationResult.rank_change,
}


class SimulationExecutionRepository(BaseRepository[SimulationExecution]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SimulationExecution)

    async def get_for_scenario(
        self, scenario_id: uuid.UUID, execution_id: uuid.UUID,
    ) -> SimulationExecution | None:
        stmt = (
            select(SimulationExecution)
            .where(
                SimulationExecution.id == execution_id,
                SimulationExecution.scenario_id == scenario_id,
            )
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_scenario(self, scenario_id: uuid.UUID) -> list[SimulationExecution]:
        stmt = (
            select(SimulationExecution)
            .where(SimulationExecution.scenario_id == scenario_id)
            .order_by(SimulationExecution.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def latest_completed(self, scenario_id: uuid.UUID) -> SimulationExecution | None:
        stmt = (
            select(SimulationExecution)
            .where(
                SimulationExecution.scenario_id == scenario_id,
                SimulationExecution.status == "completed",
            )
            .order_by(SimulationExecution.created_at.desc())
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def has_active(self, scenario_id: uuid.UUID) -> bool:
        stmt = (
            select(SimulationExecution.id)
            .where(
                SimulationExecution.scenario_id == scenario_id,
                SimulationExecution.status.in_(ACTIVE_STATUSES),
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None


class SimulationResultRepository(BaseRepository[SimulationResult]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SimulationResult)

    async def list_by_execution(self, execution_id: uuid.UUID) -> list[SimulationResult]:
        stmt = (
            select(SimulationResult)
            .where(SimulationResult.execution_id == execution_id)
            .order_by(SimulationResult.simulation_rank.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def paginated(
        self,
        execution_id: uuid.UUID,
        page: int,
        page_size: int,
        sort_by: str = "simulation_rank",
        order: str = "asc",
        change_filter: str | None = None,
    ) -> tuple[list[SimulationResult], int]:
        conditions = [SimulationResult.execution_id == execution_id]
        if change_filter and change_filter in RESULT_CHANGE_FILTERS:
            conditions.extend(RESULT_CHANGE_FILTERS[change_filter])

        count_stmt = select(func.count()).select_from(SimulationResult).where(*conditions)
        total = (await self._session.execute(count_stmt)).scalar() or 0

        column = RESULT_SORT_COLUMNS.get(sort_by, SimulationResult.simulation_rank)
        order_column = column.asc() if order == "asc" else column.desc()
        stmt = (
            select(SimulationResult)
            .where(*conditions)
            .order_by(order_column, SimulationResult.candidate_name.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all()), total

    async def top_movers(self, execution_id: uuid.UUID, limit: int = 5) -> list[SimulationResult]:
        stmt = (
            select(SimulationResult)
            .where(SimulationResult.execution_id == execution_id)
            .order_by(func.abs(SimulationResult.score_change).desc(), SimulationResult.score_change.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_execution(self, execution_id: uuid.UUID) -> None:
        stmt = delete(SimulationResult).where(SimulationResult.execution_id == execution_id)
        await self._session.execute(stmt)
        await self._session.flush()


class SimulationImpactRepository(BaseRepository[SimulationImpact]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SimulationImpact)

    async def list_by_execution(self, execution_id: uuid.UUID) -> list[SimulationImpact]:
        stmt = (
            select(SimulationImpact)
            .where(SimulationImpact.execution_id == execution_id)
            .order_by(SimulationImpact.metric.asc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def delete_by_execution(self, execution_id: uuid.UUID) -> None:
        stmt = delete(SimulationImpact).where(SimulationImpact.execution_id == execution_id)
        await self._session.execute(stmt)
        await self._session.flush()