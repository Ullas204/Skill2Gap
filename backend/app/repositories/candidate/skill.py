from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import CandidateSkill, Skill
from app.repositories.base import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Skill)

    async def find_by_name(self, name: str) -> Skill | None:
        stmt = select(Skill).where(Skill.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(self, query: str, limit: int = 20) -> list[Skill]:
        stmt = select(Skill).where(Skill.name.ilike(f"%{query}%")).limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class CandidateSkillRepository(BaseRepository[CandidateSkill]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, CandidateSkill)

    async def list_by_profile(self, profile_id) -> list[CandidateSkill]:
        stmt = (
            select(CandidateSkill)
            .where(CandidateSkill.profile_id == profile_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
