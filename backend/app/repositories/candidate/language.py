import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Language
from app.repositories.base import BaseRepository


class LanguageRepository(BaseRepository[Language]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Language)

    async def list_by_profile(self, profile_id: uuid.UUID) -> list[Language]:
        stmt = select(Language).where(Language.profile_id == profile_id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
