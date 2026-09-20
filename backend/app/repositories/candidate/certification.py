import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Certification
from app.repositories.base import BaseRepository


class CertificationRepository(BaseRepository[Certification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Certification)

    async def list_by_profile(self, profile_id: uuid.UUID) -> list[Certification]:
        stmt = select(Certification).where(Certification.profile_id == profile_id).order_by(Certification.issue_date.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
