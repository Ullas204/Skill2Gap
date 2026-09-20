import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Education
from app.repositories.base import BaseRepository


class EducationRepository(BaseRepository[Education]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Education)

    async def list_by_profile(self, profile_id: uuid.UUID) -> list[Education]:
        stmt = select(Education).where(Education.profile_id == profile_id).order_by(Education.start_date.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
