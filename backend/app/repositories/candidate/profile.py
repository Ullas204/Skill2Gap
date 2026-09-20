import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import CandidateProfile
from app.repositories.base import BaseRepository


class CandidateProfileRepository(BaseRepository[CandidateProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CandidateProfile)

    async def get_by_user_id(self, user_id: uuid.UUID) -> CandidateProfile | None:
        stmt = select(CandidateProfile).where(CandidateProfile.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, user_id: uuid.UUID, **kwargs) -> CandidateProfile:
        existing = await self.get_by_user_id(user_id)
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            await self._session.flush()
            await self._session.refresh(existing)
            return existing
        profile = CandidateProfile(user_id=user_id, **kwargs)
        self._session.add(profile)
        await self._session.flush()
        return profile
