import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.domain.models import User
from app.domain.screening_schemas import (
    AISearchRequest,
    AISearchResponse,
    CandidateAISummaryResponse,
    HiringRecommendationResponse,
    JobAISummaryResponse,
    RecruiterDashboardSummaryResponse,
    TopCandidatesResponse,
)
from app.services.screening.ai_search import AISearchService
from app.services.screening.ai_summary import AISummaryService
from app.services.screening.top_candidates import TopCandidatesService

router = APIRouter(prefix="/ai", tags=["ai-intelligence"])


def _get_search_service(db: AsyncSession = Depends(get_db)) -> AISearchService:
    return AISearchService(db)


def _get_summary_service(db: AsyncSession = Depends(get_db)) -> AISummaryService:
    return AISummaryService(db)


def _get_top_service(db: AsyncSession = Depends(get_db)) -> TopCandidatesService:
    return TopCandidatesService(db)


# ─── AI Search ────────────────────────────────────────────────────────

@router.post("/search", response_model=AISearchResponse)
async def ai_search_candidates(
    body: AISearchRequest,
    service: AISearchService = Depends(_get_search_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        result = await service.search_candidates(
            query=body.query,
            recruiter_id=current_user.id,
            job_id=body.job_id,
            limit=body.limit,
            offset=body.offset,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
    return result


# ─── Candidate AI Summary ─────────────────────────────────────────────

@router.get("/summary/{candidate_id}", response_model=CandidateAISummaryResponse)
async def get_candidate_summary(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID | None = Query(None),
    service: AISummaryService = Depends(_get_summary_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    result = await service.generate_candidate_summary(candidate_id, job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Candidate self-view ──────────────────────────────────────────────

@router.get("/my-summary", response_model=CandidateAISummaryResponse)
async def get_my_summary(
    job_id: uuid.UUID | None = Query(None),
    service: AISummaryService = Depends(_get_summary_service),
    current_user: User = Depends(require_role("candidate")),
):
    result = await service.generate_candidate_summary(current_user.id, job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Job AI Summary ───────────────────────────────────────────────────

@router.get("/job-summary/{job_id}", response_model=JobAISummaryResponse)
async def get_job_summary(
    job_id: uuid.UUID,
    service: AISummaryService = Depends(_get_summary_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    result = await service.generate_job_summary(job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Top Candidates ───────────────────────────────────────────────────

@router.get("/top-candidates", response_model=TopCandidatesResponse)
async def get_top_candidates(
    job_id: uuid.UUID | None = Query(None),
    limit: int = Query(10, ge=1, le=50),
    service: TopCandidatesService = Depends(_get_top_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    result = await service.get_top_candidates(
        recruiter_id=current_user.id,
        job_id=job_id,
        limit=limit,
    )
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Hiring Recommendation ───────────────────────────────────────────

@router.get(
    "/recommendation/{job_id}/{candidate_id}",
    response_model=HiringRecommendationResponse,
)
async def get_hiring_recommendation(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    service: TopCandidatesService = Depends(_get_top_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    result = await service.get_hiring_recommendation(job_id, candidate_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Recruiter AI Dashboard Summary ───────────────────────────────────

@router.get("/recruiter-dashboard", response_model=RecruiterDashboardSummaryResponse)
async def get_recruiter_ai_dashboard(
    service: AISummaryService = Depends(_get_summary_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    result = await service.generate_recruiter_dashboard(current_user.id)
    return result
