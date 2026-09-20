import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.domain.models import User
from app.domain.resume_intelligence_schemas import (
    ResumeCompareReport,
    ResumeIntelligenceReport,
)
from app.db.session import get_db
from app.services.candidate.resume_intelligence import ResumeIntelligenceService

router = APIRouter(prefix="/candidates/resume", tags=["resume-intelligence"])


async def _get_intelligence_service(db: AsyncSession = Depends(get_db)) -> ResumeIntelligenceService:
    return ResumeIntelligenceService(db)


@router.get("/{resume_id}/intelligence", response_model=ResumeIntelligenceReport)
async def get_resume_intelligence_report(
    resume_id: uuid.UUID,
    service: ResumeIntelligenceService = Depends(_get_intelligence_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        return await service.get_full_report(resume_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{resume_id}/intelligence/scores", response_model=dict)
async def get_resume_scores(
    resume_id: uuid.UUID,
    service: ResumeIntelligenceService = Depends(_get_intelligence_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        report = await service.get_full_report(resume_id, current_user.id)
        return report.scores.model_dump()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{resume_id}/intelligence/ats", response_model=dict)
async def get_ats_report(
    resume_id: uuid.UUID,
    service: ResumeIntelligenceService = Depends(_get_intelligence_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        report = await service.get_full_report(resume_id, current_user.id)
        return report.ats_report.model_dump()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{resume_id}/intelligence/skills", response_model=dict)
async def get_skill_analysis(
    resume_id: uuid.UUID,
    service: ResumeIntelligenceService = Depends(_get_intelligence_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        report = await service.get_full_report(resume_id, current_user.id)
        return report.skill_analysis.model_dump()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{resume_id}/intelligence/keywords", response_model=dict)
async def get_keyword_analysis(
    resume_id: uuid.UUID,
    service: ResumeIntelligenceService = Depends(_get_intelligence_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        report = await service.get_full_report(resume_id, current_user.id)
        return report.keyword_analysis.model_dump()
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{resume_id}/intelligence/recommendations", response_model=dict)
async def get_recommendations(
    resume_id: uuid.UUID,
    service: ResumeIntelligenceService = Depends(_get_intelligence_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        report = await service.get_full_report(resume_id, current_user.id)
        return {"recommendations": [r.model_dump() for r in report.recommendations]}
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{resume_id}/intelligence/compare", response_model=ResumeCompareReport)
async def compare_resume_intelligence(
    resume_id: uuid.UUID,
    service: ResumeIntelligenceService = Depends(_get_intelligence_service),
    current_user: User = Depends(require_role("candidate")),
):
    try:
        return await service.compare_versions(resume_id, current_user.id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))
