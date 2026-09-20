import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.domain.models import User
from app.domain.screening_schemas import (
    AdversarialTestResponse,
    CandidateFairnessResponse,
    FairnessMetricsResponse,
    FairnessOverviewResponse,
    FairnessReportResponse,
    JDAnalysisResponse,
)
from app.services.fairness.fairness_engine import FairnessEngine

router = APIRouter(prefix="/fairness", tags=["fairness"])


def _get_fairness_engine(db: AsyncSession = Depends(get_db)) -> FairnessEngine:
    return FairnessEngine(db)


# --- Fairness Overview ---

@router.get("/overview", response_model=FairnessOverviewResponse)
async def get_fairness_overview(
    engine: FairnessEngine = Depends(_get_fairness_engine),
    current_user: User = Depends(require_role("hr", "recruiter", "admin")),
):
    return await engine.get_fairness_overview()


# --- Fairness Metrics ---

@router.get("/metrics", response_model=FairnessMetricsResponse)
async def get_fairness_metrics(
    engine: FairnessEngine = Depends(_get_fairness_engine),
    current_user: User = Depends(require_role("hr", "recruiter", "admin")),
):
    return await engine.get_fairness_metrics()


# --- Fairness Report for Job ---

@router.get("/report/{job_id}", response_model=FairnessReportResponse)
async def get_fairness_report(
    job_id: uuid.UUID,
    engine: FairnessEngine = Depends(_get_fairness_engine),
    current_user: User = Depends(require_role("hr", "recruiter", "admin")),
):
    result = await engine.get_fairness_report(job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# --- Analyze Fairness ---

@router.post("/analyze")
async def analyze_fairness(
    job_id: uuid.UUID | None = Query(None),
    engine: FairnessEngine = Depends(_get_fairness_engine),
    current_user: User = Depends(require_role("hr", "recruiter", "admin")),
):
    result = await engine.analyze_fairness(job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# --- Detect Ranking Bias ---

@router.get("/bias-detection/{job_id}")
async def detect_ranking_bias(
    job_id: uuid.UUID,
    engine: FairnessEngine = Depends(_get_fairness_engine),
    current_user: User = Depends(require_role("hr", "recruiter", "admin")),
):
    return await engine.detect_ranking_bias(job_id)


# --- Adversarial Test ---

@router.post("/adversarial-test", response_model=AdversarialTestResponse)
async def run_adversarial_test(
    job_id: uuid.UUID = Query(...),
    candidate_id: uuid.UUID = Query(...),
    engine: FairnessEngine = Depends(_get_fairness_engine),
    current_user: User = Depends(require_role("hr", "recruiter", "admin")),
):
    result = await engine.run_adversarial_test(job_id, candidate_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# --- JD Bias Analysis ---

@router.get("/jd-analysis/{job_id}", response_model=JDAnalysisResponse)
async def analyze_job_description(
    job_id: uuid.UUID,
    engine: FairnessEngine = Depends(_get_fairness_engine),
    current_user: User = Depends(require_role("hr", "recruiter", "admin")),
):
    result = await engine.analyze_job_description(job_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# --- Bias Alerts ---

@router.get("/bias-alerts")
async def get_bias_alerts(
    limit: int = Query(50, ge=1, le=200),
    engine: FairnessEngine = Depends(_get_fairness_engine),
    current_user: User = Depends(require_role("hr", "recruiter", "admin")),
):
    return await engine.get_bias_alerts(limit)


# --- Candidate Fairness View ---

@router.get("/candidate/{candidate_id}", response_model=CandidateFairnessResponse)
async def get_candidate_fairness(
    candidate_id: uuid.UUID,
    engine: FairnessEngine = Depends(_get_fairness_engine),
    current_user: User = Depends(require_role("hr", "recruiter", "admin")),
):
    result = await engine.get_candidate_fairness(candidate_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# --- Candidate Self Fairness View ---

@router.get("/my-fairness", response_model=CandidateFairnessResponse)
async def get_my_fairness(
    engine: FairnessEngine = Depends(_get_fairness_engine),
    current_user: User = Depends(require_role("candidate")),
):
    result = await engine.get_candidate_fairness(current_user.id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
