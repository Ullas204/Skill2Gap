import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.domain.job_schemas import (
    JobApplicationDetailResponse,
    JobApplicationUpdate,
    JobCreate,
    JobListResponse,
    JobResponse,
    JobUpdate,
    RecruiterNoteCreate,
    RecruiterNoteResponse,
)
from app.domain.schemas import MessageResponse
from app.domain.models import User
from app.services.jobs.recruiter_job_service import RecruiterJobService

router = APIRouter(prefix="/recruiter/jobs", tags=["recruiter-jobs"])


def _get_service(db: AsyncSession = Depends(get_db)) -> RecruiterJobService:
    return RecruiterJobService(db)


@router.get("/dashboard")
async def get_dashboard(
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    return await service.get_recruiter_dashboard(current_user.id)


@router.post("", response_model=JobResponse, status_code=201)
async def create_job(
    body: JobCreate,
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    return await service.create_job(current_user.id, body)


@router.get("", response_model=list[JobListResponse])
async def list_jobs(
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    return await service.list_jobs(current_user.id)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: uuid.UUID,
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    job = await service.get_job(job_id, current_user.id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: uuid.UUID,
    body: JobUpdate,
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    job = await service.update_job(job_id, current_user.id, body)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.delete("/{job_id}", response_model=MessageResponse)
async def delete_job(
    job_id: uuid.UUID,
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    deleted = await service.delete_job(job_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Job not found")
    return MessageResponse(message="Job deleted")


@router.patch("/{job_id}/status", response_model=JobResponse)
async def change_job_status(
    job_id: uuid.UUID,
    status: str,
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    valid_statuses = {"draft", "published", "closed", "archived"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    job = await service.change_job_status(job_id, current_user.id, status)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/applications", response_model=list[JobApplicationDetailResponse])
async def list_applications(
    job_id: uuid.UUID,
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    return await service.get_applications_for_job(job_id, current_user.id)


@router.patch("/applications/{application_id}/status", response_model=MessageResponse)
async def update_application_status(
    application_id: uuid.UUID,
    body: JobApplicationUpdate,
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    updated = await service.update_application_status(application_id, current_user.id, body.status.value)
    if not updated:
        raise HTTPException(status_code=404, detail="Application not found")
    return MessageResponse(message=f"Application status updated to {body.status.value}")


class RecruiterNoteUpdate(BaseModel):
    note: str = Field(..., min_length=1)


@router.put("/applications/{application_id}/notes/{note_id}", response_model=RecruiterNoteResponse)
async def update_note(
    application_id: uuid.UUID,
    note_id: uuid.UUID,
    body: RecruiterNoteUpdate,
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    note = await service.update_recruiter_note(note_id, application_id, current_user.id, body.note)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.delete("/applications/{application_id}/notes/{note_id}", response_model=MessageResponse)
async def delete_note(
    application_id: uuid.UUID,
    note_id: uuid.UUID,
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    deleted = await service.delete_recruiter_note(note_id, application_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Note not found")
    return MessageResponse(message="Note deleted")


@router.post("/applications/{application_id}/notes", response_model=RecruiterNoteResponse, status_code=201)
async def add_note(
    application_id: uuid.UUID,
    body: RecruiterNoteCreate,
    service: RecruiterJobService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    note = await service.add_recruiter_note(application_id, current_user.id, body)
    if not note:
        raise HTTPException(status_code=404, detail="Application not found")
    return note
