import uuid

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Job, JobApplication, SavedJob
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Job)

    async def list_by_recruiter(self, recruiter_id: uuid.UUID) -> list[Job]:
        stmt = select(Job).where(Job.recruiter_id == recruiter_id).order_by(Job.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_recruiter(self, job_id: uuid.UUID, recruiter_id: uuid.UUID) -> Job | None:
        stmt = select(Job).where(Job.id == job_id, Job.recruiter_id == recruiter_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def search(
        self,
        q: str | None = None,
        employment_type: str | None = None,
        location: str | None = None,
        salary_min: int | None = None,
        salary_max: int | None = None,
        skills: list[str] | None = None,
        status: str | None = "published",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Job], int]:
        conditions = [Job.is_archived == False]
        if status:
            conditions.append(Job.status == status)
        else:
            conditions.append(Job.status.in_(["published", "closed"]))
        if q:
            conditions.append(
                or_(
                    Job.title.ilike(f"%{q}%"),
                    Job.company.ilike(f"%{q}%"),
                    Job.description.ilike(f"%{q}%"),
                    Job.location.ilike(f"%{q}%"),
                )
            )
        if employment_type:
            conditions.append(Job.employment_type == employment_type)
        if location:
            conditions.append(Job.location.ilike(f"%{location}%"))
        if salary_min is not None:
            conditions.append(
                or_(Job.salary_max >= salary_min, Job.salary_min >= salary_min)
            )
        if salary_max is not None:
            conditions.append(
                or_(Job.salary_min <= salary_max, Job.salary_max <= salary_max)
            )
        if skills:
            for skill in skills:
                conditions.append(Job.required_skills.any(skill))

        stmt_count = select(func.count()).select_from(Job).where(*conditions)
        total_result = await self._session.execute(stmt_count)
        total = total_result.scalar() or 0

        offset = (page - 1) * page_size
        stmt = select(Job).where(*conditions).order_by(Job.created_at.desc()).offset(offset).limit(page_size)
        result = await self._session.execute(stmt)
        items = list(result.scalars().all())
        return items, total

    async def increment_version(self, job_id: uuid.UUID) -> Job | None:
        stmt = (
            update(Job).where(Job.id == job_id).values(version=Job.version + 1).returning(Job)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()


class JobApplicationRepository(BaseRepository[JobApplication]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, JobApplication)

    async def list_by_job(self, job_id: uuid.UUID) -> list[JobApplication]:
        stmt = (
            select(JobApplication)
            .options(selectinload(JobApplication.recruiter_notes))
            .where(JobApplication.job_id == job_id)
            .order_by(JobApplication.created_at.desc())
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_candidate(self, candidate_id: uuid.UUID) -> list[JobApplication]:
        stmt = select(JobApplication).where(JobApplication.candidate_id == candidate_id).order_by(JobApplication.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_job_and_candidate(self, job_id: uuid.UUID, candidate_id: uuid.UUID) -> JobApplication | None:
        stmt = select(JobApplication).where(
            JobApplication.job_id == job_id,
            JobApplication.candidate_id == candidate_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_by_job(self, job_id: uuid.UUID) -> int:
        stmt = select(func.count()).select_from(JobApplication).where(JobApplication.job_id == job_id)
        result = await self._session.execute(stmt)
        return result.scalar() or 0

    async def update_status(self, application_id: uuid.UUID, status: str) -> JobApplication | None:
        stmt = (
            update(JobApplication)
            .where(JobApplication.id == application_id)
            .values(status=status)
            .returning(JobApplication)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()


class SavedJobRepository(BaseRepository[SavedJob]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, SavedJob)

    async def list_by_candidate(self, candidate_id: uuid.UUID) -> list[SavedJob]:
        stmt = select(SavedJob).where(SavedJob.candidate_id == candidate_id).order_by(SavedJob.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def is_saved(self, candidate_id: uuid.UUID, job_id: uuid.UUID) -> bool:
        stmt = select(SavedJob).where(
            SavedJob.candidate_id == candidate_id,
            SavedJob.job_id == job_id,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def remove(self, candidate_id: uuid.UUID, job_id: uuid.UUID) -> bool:
        stmt = select(SavedJob).where(
            SavedJob.candidate_id == candidate_id,
            SavedJob.job_id == job_id,
        )
        result = await self._session.execute(stmt)
        saved = result.scalar_one_or_none()
        if saved:
            await self._session.delete(saved)
            await self._session.flush()
            return True
        return False
