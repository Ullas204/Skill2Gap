import logging
import uuid

from sqlalchemy import update as sa_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ApplicationStatus, NotificationType
from app.domain.job_schemas import JobCreate, JobUpdate, RecruiterNoteCreate
from app.domain.models import Job, JobApplication, Notification, RecruiterNote, User
from app.repositories.jobs.job import JobApplicationRepository, JobRepository
from app.repositories.user import UserRepository

logger = logging.getLogger(__name__)
AUDIT_LOGGER = logging.getLogger("audit")


class RecruiterJobService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.job_repo = JobRepository(session)
        self.application_repo = JobApplicationRepository(session)
        self.user_repo = UserRepository(session)

    async def create_job(self, recruiter_id: uuid.UUID, data: JobCreate) -> Job:
        job = await self.job_repo.create(
            recruiter_id=recruiter_id,
            title=data.title,
            company=data.company,
            department=data.department,
            employment_type=data.employment_type.value,
            experience_required=data.experience_required,
            education_required=data.education_required,
            required_skills=data.required_skills,
            preferred_skills=data.preferred_skills,
            location=data.location,
            salary_min=data.salary_min,
            salary_max=data.salary_max,
            salary_currency=data.salary_currency,
            description=data.description,
            benefits=data.benefits,
            application_deadline=data.application_deadline,
            status=data.status.value,
        )
        AUDIT_LOGGER.info(
            "JOB_CREATE | recruiter=%s job=%s title=%s",
            recruiter_id, job.id, job.title,
        )
        return job

    async def update_job(self, job_id: uuid.UUID, recruiter_id: uuid.UUID, data: JobUpdate) -> Job | None:
        job = await self.job_repo.get_by_recruiter(job_id, recruiter_id)
        if not job:
            return None
        update_kwargs = data.model_dump(exclude_unset=True)
        if update_kwargs.get("employment_type"):
            update_kwargs["employment_type"] = update_kwargs["employment_type"].value
        if update_kwargs.get("status"):
            update_kwargs["status"] = update_kwargs["status"].value
        if update_kwargs:
            update_kwargs["version"] = job.version + 1
        updated = await self.job_repo.update(job_id, **update_kwargs)
        AUDIT_LOGGER.info(
            "JOB_UPDATE | recruiter=%s job=%s fields=%s",
            recruiter_id, job_id, list(update_kwargs.keys()),
        )
        return updated

    async def get_job(self, job_id: uuid.UUID, recruiter_id: uuid.UUID) -> Job | None:
        return await self.job_repo.get_by_recruiter(job_id, recruiter_id)

    async def list_jobs(self, recruiter_id: uuid.UUID) -> list[dict]:
        jobs = await self.job_repo.list_by_recruiter(recruiter_id)
        result = []
        for job in jobs:
            count = await self.application_repo.count_by_job(job.id)
            result.append({
                "id": job.id,
                "recruiter_id": job.recruiter_id,
                "title": job.title,
                "company": job.company,
                "department": job.department,
                "employment_type": job.employment_type,
                "location": job.location,
                "salary_min": job.salary_min,
                "salary_max": job.salary_max,
                "salary_currency": job.salary_currency,
                "status": job.status,
                "application_deadline": job.application_deadline,
                "application_count": count,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
            })
        return result

    async def delete_job(self, job_id: uuid.UUID, recruiter_id: uuid.UUID) -> bool:
        job = await self.job_repo.get_by_recruiter(job_id, recruiter_id)
        if not job:
            return False
        await self.session.delete(job)
        await self.session.flush()
        AUDIT_LOGGER.info("JOB_DELETE | recruiter=%s job=%s", recruiter_id, job_id)
        return True

    async def change_job_status(self, job_id: uuid.UUID, recruiter_id: uuid.UUID, status: str) -> Job | None:
        job = await self.job_repo.get_by_recruiter(job_id, recruiter_id)
        if not job:
            return None
        updated = await self.job_repo.update(job_id, status=status, version=job.version + 1)
        AUDIT_LOGGER.info(
            "JOB_STATUS_CHANGE | recruiter=%s job=%s status=%s",
            recruiter_id, job_id, status,
        )
        return updated

    async def get_applications_for_job(self, job_id: uuid.UUID, recruiter_id: uuid.UUID) -> list[dict]:
        job = await self.job_repo.get_by_recruiter(job_id, recruiter_id)
        if not job:
            return []
        applications = await self.application_repo.list_by_job(job_id)
        result = []
        for app in applications:
            candidate = await self.user_repo.get(app.candidate_id)
            notes = []
            for note in app.recruiter_notes:
                notes.append({
                    "id": note.id,
                    "job_application_id": note.job_application_id,
                    "recruiter_id": note.recruiter_id,
                    "note": note.note,
                    "created_at": note.created_at,
                    "updated_at": note.updated_at,
                })
            result.append({
                "id": app.id,
                "job_id": app.job_id,
                "candidate_id": app.candidate_id,
                "resume_id": app.resume_id,
                "cover_letter": app.cover_letter,
                "status": app.status,
                "created_at": app.created_at,
                "updated_at": app.updated_at,
                "candidate_name": candidate.full_name if candidate else "",
                "candidate_email": candidate.email if candidate else "",
                "job_title": job.title,
                "recruiter_notes": notes,
            })
        return result

    async def update_application_status(
        self, application_id: uuid.UUID, recruiter_id: uuid.UUID, status: str,
    ) -> JobApplication | None:
        app = await self.application_repo.get(application_id)
        if not app:
            return None
        job = await self.job_repo.get(app.job_id)
        if not job or job.recruiter_id != recruiter_id:
            return None
        updated = await self.application_repo.update_status(application_id, status)
        notification = Notification(
            user_id=app.candidate_id,
            title="Application Status Updated",
            message=f"Your application for '{job.title}' has been updated to {status.replace('_', ' ').title()}",
            notification_type=NotificationType.APPLICATION_STATUS,
        )
        self.session.add(notification)
        await self.session.flush()
        AUDIT_LOGGER.info(
            "APPLICATION_STATUS | recruiter=%s application=%s status=%s",
            recruiter_id, application_id, status,
        )
        return updated

    async def add_recruiter_note(
        self, application_id: uuid.UUID, recruiter_id: uuid.UUID, data: RecruiterNoteCreate,
    ) -> RecruiterNote | None:
        app = await self.application_repo.get(application_id)
        if not app:
            return None
        job = await self.job_repo.get(app.job_id)
        if not job or job.recruiter_id != recruiter_id:
            return None
        note = RecruiterNote(
            job_application_id=application_id,
            recruiter_id=recruiter_id,
            note=data.note,
        )
        self.session.add(note)
        await self.session.flush()
        return note

    async def update_recruiter_note(
        self, note_id: uuid.UUID, application_id: uuid.UUID, recruiter_id: uuid.UUID, note_text: str,
    ) -> RecruiterNote | None:
        app = await self.application_repo.get(application_id)
        if not app:
            return None
        job = await self.job_repo.get(app.job_id)
        if not job or job.recruiter_id != recruiter_id:
            return None
        stmt = (
            sa_update(RecruiterNote)
            .where(RecruiterNote.id == note_id, RecruiterNote.recruiter_id == recruiter_id)
            .values(note=note_text)
            .returning(RecruiterNote)
        )
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.scalar_one_or_none()

    async def delete_recruiter_note(
        self, note_id: uuid.UUID, application_id: uuid.UUID, recruiter_id: uuid.UUID,
    ) -> bool:
        app = await self.application_repo.get(application_id)
        if not app:
            return False
        job = await self.job_repo.get(app.job_id)
        if not job or job.recruiter_id != recruiter_id:
            return False
        note = await self.session.get(RecruiterNote, note_id)
        if not note or note.recruiter_id != recruiter_id or note.job_application_id != application_id:
            return False
        await self.session.delete(note)
        await self.session.flush()
        return True

    async def get_recruiter_dashboard(self, recruiter_id: uuid.UUID) -> dict:
        jobs = await self.job_repo.list_by_recruiter(recruiter_id)
        total_jobs = len(jobs)
        published = sum(1 for j in jobs if j.status == "published")
        draft = sum(1 for j in jobs if j.status == "draft")
        closed = sum(1 for j in jobs if j.status == "closed")
        total_applications = 0
        recent_applications = []
        for job in jobs:
            apps = await self.application_repo.list_by_job(job.id)
            total_applications += len(apps)
            for app in apps[:5]:
                candidate = await self.user_repo.get(app.candidate_id)
                recent_applications.append({
                    "id": app.id,
                    "job_title": job.title,
                    "candidate_name": candidate.full_name if candidate else "",
                    "status": app.status,
                    "created_at": app.created_at,
                })
        recent_applications.sort(key=lambda x: x["created_at"], reverse=True)
        recent_applications = recent_applications[:10]
        return {
            "total_jobs": total_jobs,
            "published_jobs": published,
            "draft_jobs": draft,
            "closed_jobs": closed,
            "total_applications": total_applications,
            "recent_applications": recent_applications,
        }
