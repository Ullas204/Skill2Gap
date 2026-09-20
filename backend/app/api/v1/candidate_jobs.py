import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.domain.job_schemas import (
    JobApplicationCreate,
    JobApplicationListItem,
    JobApplicationResponse,
    JobCreate,
    JobListResponse,
    JobResponse,
    JobSearchParams,
    JobSearchResponse,
    SavedJobResponse,
)
from app.domain.models import User
from app.domain.schemas import MessageResponse
from app.services.jobs.candidate_job_service import CandidateJobService

router = APIRouter(prefix="/candidate/jobs", tags=["candidate-jobs"])


def _get_service(db: AsyncSession = Depends(get_db)) -> CandidateJobService:
    return CandidateJobService(db)


@router.get("/dashboard")
async def get_dashboard(
    service: CandidateJobService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    return await service.get_candidate_dashboard(current_user.id)


@router.get("/search", response_model=JobSearchResponse)
async def search_jobs(
    q: str | None = None,
    employment_type: str | None = None,
    location: str | None = None,
    salary_min: int | None = None,
    salary_max: int | None = None,
    skills: str | None = None,
    status: str | None = "published",
    page: int = 1,
    page_size: int = 20,
    service: CandidateJobService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    skill_list = skills.split(",") if skills else None
    params = JobSearchParams(
        q=q,
        employment_type=employment_type,
        location=location,
        salary_min=salary_min,
        salary_max=salary_max,
        skills=skill_list,
        status=status,
        page=page,
        page_size=page_size,
    )
    return await service.search_jobs(params)


@router.post("/apply", response_model=JobApplicationResponse, status_code=201)
async def apply_for_job(
    body: JobApplicationCreate,
    service: CandidateJobService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        return await service.apply(current_user.id, body)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/applications", response_model=list[JobApplicationListItem])
async def my_applications(
    service: CandidateJobService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    return await service.get_my_applications(current_user.id)


@router.post("/applications/{application_id}/withdraw", response_model=MessageResponse)
async def withdraw_application(
    application_id: uuid.UUID,
    service: CandidateJobService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        withdrawn = await service.withdraw_application(application_id, current_user.id)
        if not withdrawn:
            raise HTTPException(status_code=404, detail="Application not found")
        return {"message": "Application withdrawn"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/saved", response_model=SavedJobResponse, status_code=201)
async def save_job(
    job_id: uuid.UUID,
    service: CandidateJobService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        saved = await service.save_job(current_user.id, job_id)
        return SavedJobResponse(job_id=saved.job_id, created_at=saved.created_at)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/saved", response_model=list[JobListResponse])
async def saved_jobs(
    service: CandidateJobService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    return await service.get_saved_jobs(current_user.id)


@router.delete("/saved/{job_id}", response_model=MessageResponse)
async def unsave_job(
    job_id: uuid.UUID,
    service: CandidateJobService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    removed = await service.unsave_job(current_user.id, job_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Saved job not found")
    return MessageResponse(message="Job unsaved")


@router.get("/{job_id}", response_model=JobResponse)
async def get_job_detail(
    job_id: uuid.UUID,
    service: CandidateJobService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    job = await service.get_job_detail(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or unavailable")
    return job
