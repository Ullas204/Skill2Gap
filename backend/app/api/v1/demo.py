"""API endpoints for the AI Demo Data Generator & Recruitment Simulation Platform."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.domain.demo_schemas import (
    DemoCustomRequest,
    DemoExportResponse,
    DemoGenerateRequest,
    DemoRunDetailResponse,
    DemoRunResponse,
    DemoScenarioResponse,
    DemoStatusResponse,
)
from app.domain.models import User
from app.domain.schemas import MessageResponse
from app.services.demo.demo_service import DemoService

router = APIRouter(prefix="/demo", tags=["demo"])

_demo_service = DemoService()


def _get_demo_service() -> DemoService:
    return _demo_service


@router.get("/scenarios", response_model=list[DemoScenarioResponse])
async def list_scenarios(
    service: DemoService = Depends(_get_demo_service),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    return await service.list_scenarios(db)


@router.post("/generate", response_model=DemoRunResponse)
async def generate(
    body: DemoGenerateRequest,
    background_tasks: BackgroundTasks,
    service: DemoService = Depends(_get_demo_service),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    run = await service.start_generation(db, body, admin.id, background_tasks)
    return DemoRunResponse.model_validate(run)


@router.post("/custom", response_model=DemoRunResponse)
async def generate_custom(
    body: DemoCustomRequest,
    background_tasks: BackgroundTasks,
    service: DemoService = Depends(_get_demo_service),
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_role("admin")),
):
    run = await service.start_generation(db, body, admin.id, background_tasks)
    return DemoRunResponse.model_validate(run)


@router.get("/status", response_model=DemoStatusResponse)
async def get_status(
    service: DemoService = Depends(_get_demo_service),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    return await service.get_status(db)


@router.get("/runs/{run_id}", response_model=DemoRunDetailResponse)
async def get_run_detail(
    run_id: uuid.UUID = Path(...),
    service: DemoService = Depends(_get_demo_service),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    detail = await service.get_run_detail(db, run_id)
    if detail is None:
        raise NotFoundError(detail="Demo run not found")
    return detail


@router.post("/reset", response_model=MessageResponse)
async def reset_demo(
    service: DemoService = Depends(_get_demo_service),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    counts = await service.reset(db)
    message = (
        f"Demo dataset reset complete: {counts['users_deleted']} users, "
        f"{counts['jobs_deleted']} jobs, {counts['resumes_deleted']} resumes, "
        f"{counts['interviews_deleted']} interviews, {counts['screenings_deleted']} screenings"
    )
    return MessageResponse(message=message, detail=str(counts))


@router.get("/export", response_model=DemoExportResponse)
async def export_demo(
    service: DemoService = Depends(_get_demo_service),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin")),
):
    return await service.export_dataset(db)
