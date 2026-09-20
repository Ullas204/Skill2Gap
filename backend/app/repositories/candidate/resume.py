import uuid

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ResumeStatus
from app.domain.models import ParsedResumeData, Resume, ResumeAnalysis
from app.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[Resume]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Resume)

    async def list_by_user(self, user_id: uuid.UUID) -> list[Resume]:
        stmt = select(Resume).where(Resume.user_id == user_id).order_by(Resume.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_user(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> Resume | None:
        stmt = select(Resume).where(Resume.id == resume_id, Resume.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_hash(self, file_hash: str, user_id: uuid.UUID) -> Resume | None:
        stmt = select(Resume).where(Resume.file_hash == file_hash, Resume.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_primary(self, user_id: uuid.UUID) -> Resume | None:
        stmt = select(Resume).where(Resume.user_id == user_id, Resume.is_primary == True)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def set_primary(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> None:
        await self._session.execute(
            update(Resume).where(Resume.user_id == user_id).values(is_primary=False)
        )
        await self._session.execute(
            update(Resume).where(Resume.id == resume_id, Resume.user_id == user_id).values(is_primary=True)
        )
        await self._session.flush()

    async def update_status(self, resume_id: uuid.UUID, status: ResumeStatus) -> Resume | None:
        stmt = update(Resume).where(Resume.id == resume_id).values(status=status).returning(Resume)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()

    async def get_max_version(self, user_id: uuid.UUID) -> int:
        stmt = select(Resume.version).where(Resume.user_id == user_id).order_by(Resume.version.desc()).limit(1)
        result = await self._session.execute(stmt)
        row = result.scalar_one_or_none()
        return row or 0

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(Resume).where(Resume.user_id == user_id)
        result = await self._session.execute(stmt)
        return result.scalar() or 0


class ParsedResumeDataRepository(BaseRepository[ParsedResumeData]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ParsedResumeData)

    async def get_by_resume(self, resume_id: uuid.UUID) -> ParsedResumeData | None:
        stmt = select(ParsedResumeData).where(ParsedResumeData.resume_id == resume_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_parsed(self, resume_id: uuid.UUID, **kwargs) -> ParsedResumeData:
        existing = await self.get_by_resume(resume_id)
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            await self._session.flush()
            return existing
        data = ParsedResumeData(resume_id=resume_id, **kwargs)
        self._session.add(data)
        await self._session.flush()
        return data


class ResumeAnalysisRepository(BaseRepository[ResumeAnalysis]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, ResumeAnalysis)

    async def get_by_resume(self, resume_id: uuid.UUID) -> ResumeAnalysis | None:
        stmt = select(ResumeAnalysis).where(ResumeAnalysis.resume_id == resume_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_analysis(self, resume_id: uuid.UUID, **kwargs) -> ResumeAnalysis:
        existing = await self.get_by_resume(resume_id)
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            await self._session.flush()
            return existing
        analysis = ResumeAnalysis(resume_id=resume_id, **kwargs)
        self._session.add(analysis)
        await self._session.flush()
        return analysis
