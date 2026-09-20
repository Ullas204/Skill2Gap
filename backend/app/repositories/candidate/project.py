import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Project)

    async def list_by_profile(self, profile_id: uuid.UUID) -> list[Project]:
        stmt = select(Project).where(Project.profile_id == profile_id).order_by(Project.start_date.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
