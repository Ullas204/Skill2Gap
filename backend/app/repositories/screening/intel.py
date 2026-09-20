import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import CandidateEvidenceIntel
from app.repositories.base import BaseRepository


class CandidateEvidenceIntelRepository(BaseRepository[CandidateEvidenceIntel]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CandidateEvidenceIntel)

    async def get_by_candidate(
        self, candidate_id: uuid.UUID,
    ) -> CandidateEvidenceIntel | None:
        stmt = select(CandidateEvidenceIntel).where(
            CandidateEvidenceIntel.candidate_id == candidate_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()
