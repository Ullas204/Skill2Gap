import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Experience
from app.repositories.base import BaseRepository


class ExperienceRepository(BaseRepository[Experience]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Experience)

    async def list_by_profile(self, profile_id: uuid.UUID) -> list[Experience]:
        stmt = select(Experience).where(Experience.profile_id == profile_id).order_by(Experience.start_date.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
