import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import JobFitAnalysis, JobRequirementExtraction
from app.repositories.base import BaseRepository


class JobRequirementExtractionRepository(BaseRepository[JobRequirementExtraction]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, JobRequirementExtraction)

    async def get_by_job(self, job_id: uuid.UUID) -> JobRequirementExtraction | None:
        stmt = select(JobRequirementExtraction).where(
            JobRequirementExtraction.job_id == job_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class JobFitAnalysisRepository(BaseRepository[JobFitAnalysis]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, JobFitAnalysis)

    async def get_by_job_and_candidate(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID,
    ) -> JobFitAnalysis | None:
        stmt = select(JobFitAnalysis).where(
            JobFitAnalysis.job_id == job_id,
            JobFitAnalysis.candidate_id == candidate_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
