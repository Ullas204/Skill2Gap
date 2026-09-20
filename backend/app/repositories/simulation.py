"""Repository for Simulation Scenario persistence."""
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Job  # noqa: F401  (SQLAlchemy relationship target)
from app.domain.simulation_models import SimulationScenario
from app.repositories.base import BaseRepository


class SimulationRepository(BaseRepository[SimulationScenario]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SimulationScenario)

    async def get_with_details(self, simulation_id: uuid.UUID) -> SimulationScenario | None:
        stmt = (
            select(SimulationScenario)
            .options(
                selectinload(SimulationScenario.job),
                selectinload(SimulationScenario.creator),
                selectinload(SimulationScenario.organization),
            )
            .where(SimulationScenario.id == simulation_id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_job(self, job_id: uuid.UUID) -> list[SimulationScenario]:
        stmt = (
            select(SimulationScenario)
            .options(selectinload(SimulationScenario.job))
            .where(SimulationScenario.job_id == job_id)
            .order_by(SimulationScenario.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_creator(self, user_id: uuid.UUID) -> list[SimulationScenario]:
        stmt = (
            select(SimulationScenario)
            .options(
                selectinload(SimulationScenario.job),
                selectinload(SimulationScenario.creator),
            )
            .where(SimulationScenario.created_by == user_id)
            .order_by(SimulationScenario.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_org(self, organization_id: uuid.UUID) -> list[SimulationScenario]:
        stmt = (
            select(SimulationScenario)
            .options(
                selectinload(SimulationScenario.job),
                selectinload(SimulationScenario.creator),
            )
            .where(SimulationScenario.organization_id == organization_id)
            .order_by(SimulationScenario.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_visible(
        self, user_id: uuid.UUID, organization_ids: list[uuid.UUID],
    ) -> list[SimulationScenario]:
        """Scenarios the user may see: their own, plus those created in any of
        the organizations they belong to."""
        stmt = (
            select(SimulationScenario)
            .options(
                selectinload(SimulationScenario.job),
                selectinload(SimulationScenario.creator),
            )
            .where(
                (SimulationScenario.created_by == user_id)
                | (
                    SimulationScenario.organization_id.is_not(None)
                    & SimulationScenario.organization_id.in_(organization_ids)
                )
            )
            .order_by(SimulationScenario.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def count_by_status(self, user_id: uuid.UUID, organization_ids: list[uuid.UUID]) -> dict[str, int]:
        stmt = (
            select(SimulationScenario.status, func.count())
            .where(
                (SimulationScenario.created_by == user_id)
                | (
                    SimulationScenario.organization_id.is_not(None)
                    & SimulationScenario.organization_id.in_(organization_ids)
                )
            )
            .group_by(SimulationScenario.status)
        )
        result = await self._session.execute(stmt)
        counts = {status: count for status, count in result.all()}
        return counts