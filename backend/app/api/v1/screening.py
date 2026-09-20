import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.domain.fit_schemas import FitResponse
from app.domain.intel_schemas import (
    EvidenceIntelligenceResponse,
    JobIntelligenceResponse,
)
from app.domain.models import User
from app.domain.screening_schemas import (
    CandidateComparisonRequest,
    CandidateComparisonResponse,
    CandidateMatchReportResponse,
    RankingListResponse,
    ScreeningConfig,
    ScreeningResultResponse,
    ScreeningTriggerResponse,
    SkillGapResponse,
)
from app.domain.schemas import MessageResponse
from app.services.screening.access import (
    CandidateNotAccessibleError,
    JobAccessDeniedError,
    JobNotFoundError,
    authorize_job_access,
)
from app.services.screening.fit_service import FitService
from app.services.screening.intel_service import CandidateIntelService
from app.services.screening.screening_service import ScreeningService

router = APIRouter(prefix="/screening", tags=["screening"])


def _get_service(db: AsyncSession = Depends(get_db)) -> ScreeningService:
    return ScreeningService(db)


def _get_fit_service(db: AsyncSession = Depends(get_db)) -> FitService:
    return FitService(db)


def _get_intel_service(db: AsyncSession = Depends(get_db)) -> CandidateIntelService:
    return CandidateIntelService(db)


def _http_status_for_access_error(exc: Exception) -> HTTPException:
    if isinstance(exc, JobNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=403, detail=str(exc))


# ─── Recruiter: trigger screening ──────────────────────────────────

@router.post("/jobs/{job_id}/screen", response_model=ScreeningTriggerResponse)
async def screen_job_applicants(
    job_id: uuid.UUID,
    config: ScreeningConfig | None = None,
    service: ScreeningService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    weights = config.weights.model_dump() if config and config.weights else None
    try:
        job, count = await service.screen_job_applicants(job_id, current_user.id, weights)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return ScreeningTriggerResponse(
        message=f"Screened {count} candidate(s) for '{job.title}'",
        job_id=job_id,
        candidates_screened=count,
    )


# ─── Recruiter: get ranked applicants ──────────────────────────────

@router.get("/jobs/{job_id}/rankings", response_model=RankingListResponse)
async def get_rankings(
    job_id: uuid.UUID,
    service: ScreeningService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        job, rankings = await service.get_ranked_applicants(job_id, current_user.id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    items = []
    for r in rankings:
        user = await service.session.get(User, r.candidate_id)
        items.append({
            "id": r.id,
            "job_id": r.job_id,
            "candidate_id": r.candidate_id,
            "candidate_name": user.full_name if user else "",
            "candidate_email": user.email if user else "",
            "screening_result_id": r.screening_result_id,
            "rank": r.rank,
            "previous_rank": r.previous_rank,
            "rank_change": r.rank_change,
            "overall_score": r.overall_score,
            "strength_level": r.strength_level,
            "created_at": r.created_at,
            "updated_at": r.updated_at,
        })
    return RankingListResponse(
        items=items,
        total=len(items),
        job_id=job_id,
        job_title=job.title,
    )


# ─── Recruiter: get screening detail for a candidate ───────────────

@router.get("/jobs/{job_id}/candidates/{candidate_id}", response_model=ScreeningResultResponse)
async def get_screening_result(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    service: ScreeningService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        await authorize_job_access(service.session, job_id, current_user)
    except (JobNotFoundError, JobAccessDeniedError) as exc:
        raise _http_status_for_access_error(exc)
    result = await service.get_candidate_match_report(job_id, candidate_id)
    if not result:
        raise HTTPException(status_code=404, detail="Screening result not found")
    return result["screening"]


# ─── Recruiter: skill gap for a candidate ──────────────────────────

@router.get("/jobs/{job_id}/candidates/{candidate_id}/skill-gap", response_model=SkillGapResponse)
async def get_skill_gap(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    service: ScreeningService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        await authorize_job_access(service.session, job_id, current_user)
    except (JobNotFoundError, JobAccessDeniedError) as exc:
        raise _http_status_for_access_error(exc)
    result = await service.get_candidate_match_report(job_id, candidate_id)
    if not result or not result["skill_gap"]:
        raise HTTPException(status_code=404, detail="Skill gap analysis not found")
    return result["skill_gap"]


# ─── Recruiter: compare candidates ─────────────────────────────────

@router.post("/jobs/{job_id}/compare", response_model=CandidateComparisonResponse)
async def compare_candidates(
    job_id: uuid.UUID,
    body: CandidateComparisonRequest,
    service: ScreeningService = Depends(_get_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        result = await service.compare_candidates(
            job_id, body.candidate_ids, current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return result


# ─── Recruiter: evidence-grounded fit analysis (Phase 2) ───────────

@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/fit",
    response_model=FitResponse,
)
async def get_candidate_fit(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    service: FitService = Depends(_get_fit_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        return await service.get_fit(job_id, candidate_id, current_user)
    except (JobNotFoundError, JobAccessDeniedError, CandidateNotAccessibleError) as exc:
        raise _http_status_for_access_error(exc)


# ─── Recruiter: candidate evidence intelligence (Phase 3) ──────────

@router.get(
    "/candidates/{candidate_id}/intelligence",
    response_model=EvidenceIntelligenceResponse,
)
async def get_candidate_intelligence(
    candidate_id: uuid.UUID,
    service: CandidateIntelService = Depends(_get_intel_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        return await service.get_intel(candidate_id, current_user)
    except CandidateNotAccessibleError as exc:
        raise HTTPException(status_code=403, detail=str(exc))


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/intelligence",
    response_model=JobIntelligenceResponse,
)
async def get_candidate_job_intelligence(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    service: CandidateIntelService = Depends(_get_intel_service),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    try:
        return await service.get_job_intel(job_id, candidate_id, current_user)
    except (JobNotFoundError, JobAccessDeniedError, CandidateNotAccessibleError) as exc:
        raise _http_status_for_access_error(exc)


# ─── Candidate: my match for a job ─────────────────────────────────

@router.get("/jobs/{job_id}/my-match", response_model=CandidateMatchReportResponse)
async def get_my_match(
    job_id: uuid.UUID,
    service: ScreeningService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    result = await service.get_my_match_for_job(job_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="No screening result found for this job")
    screening_resp = ScreeningResultResponse.model_validate(result["screening"]) if result.get("screening") else None
    skill_gap_resp = SkillGapResponse.model_validate(result["skill_gap"]) if result.get("skill_gap") else None
    return CandidateMatchReportResponse(
        job_id=result["job_id"],
        job_title=result["job_title"],
        candidate_id=result["candidate_id"],
        candidate_name=result["candidate_name"],
        screening=screening_resp,
        skill_gap=skill_gap_resp,
        interview_readiness_score=result.get("interview_readiness_score"),
        improvement_suggestions=result.get("improvement_suggestions"),
    )


# ─── Candidate: my screenings overview ─────────────────────────────

@router.get("/my-scores", response_model=list[ScreeningResultResponse])
async def get_my_screenings(
    service: ScreeningService = Depends(_get_service),
    current_user: User = Depends(require_role("candidate")),
):
    results = await service.screening_repo.list_by_candidate(current_user.id)
    return results
