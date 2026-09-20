import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.domain.models import User
from app.domain.screening_schemas import (
    CandidateCompareRequest,
    CandidateCompareResponse,
    CandidateExplanationResponse,
    ConfidenceResponse,
    FeatureImportanceResponse,
    RecommendationsResponse,
)
from app.services.screening.xai_engine import XAIEngine

router = APIRouter(prefix="/xai", tags=["xai"])


def _get_xai_engine(db: AsyncSession = Depends(get_db)) -> XAIEngine:
    return XAIEngine(db)


# ─── Full candidate explanation ─────────────────────────────────────

@router.get(
    "/explain/{candidate_id}",
    response_model=CandidateExplanationResponse,
)
async def explain_candidate(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID | None = Query(None),
    engine: XAIEngine = Depends(_get_xai_engine),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    result = await engine.explain_candidate(candidate_id, job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Candidate self-explanation ─────────────────────────────────────

@router.get(
    "/my-explain",
    response_model=CandidateExplanationResponse,
)
async def explain_myself(
    job_id: uuid.UUID | None = Query(None),
    engine: XAIEngine = Depends(_get_xai_engine),
    current_user: User = Depends(require_role("candidate")),
):
    result = await engine.explain_candidate(current_user.id, job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Feature importance ─────────────────────────────────────────────

@router.get(
    "/features/{candidate_id}",
    response_model=FeatureImportanceResponse,
)
async def get_feature_importance(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID | None = Query(None),
    engine: XAIEngine = Depends(_get_xai_engine),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    result = await engine.get_feature_importance(candidate_id, job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Confidence score ───────────────────────────────────────────────

@router.get(
    "/confidence/{candidate_id}",
    response_model=ConfidenceResponse,
)
async def get_confidence(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID | None = Query(None),
    engine: XAIEngine = Depends(_get_xai_engine),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    result = await engine.get_confidence_score(candidate_id, job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Recommendations ────────────────────────────────────────────────

@router.get(
    "/recommendations/{candidate_id}",
    response_model=RecommendationsResponse,
)
async def get_recommendations(
    candidate_id: uuid.UUID,
    job_id: uuid.UUID | None = Query(None),
    engine: XAIEngine = Depends(_get_xai_engine),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    result = await engine.get_recommendations(candidate_id, job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Candidate self-recommendations ─────────────────────────────────

@router.get(
    "/my-recommendations",
    response_model=RecommendationsResponse,
)
async def get_my_recommendations(
    job_id: uuid.UUID | None = Query(None),
    engine: XAIEngine = Depends(_get_xai_engine),
    current_user: User = Depends(require_role("candidate")),
):
    result = await engine.get_recommendations(current_user.id, job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ─── Candidate comparison ───────────────────────────────────────────

@router.post(
    "/compare",
    response_model=CandidateCompareResponse,
)
async def compare_candidates(
    body: CandidateCompareRequest,
    engine: XAIEngine = Depends(_get_xai_engine),
    current_user: User = Depends(require_role("hr", "recruiter")),
):
    result = await engine.compare_candidates(body.candidate_ids, body.job_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result
