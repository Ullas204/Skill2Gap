"""Analytics API — RBAC-protected endpoints for all analytics modules."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_role
from app.db.session import get_db
from app.domain.analytics_schemas import (
    AlertRuleCreateRequest,
    AlertRuleResponse,
    AIInsightsResponse,
    AdminAnalyticsResponse,
    CandidatePerformanceResponse,
    DashboardLayoutRequest,
    DashboardLayoutResponse,
    ExecutiveKPIsResponse,
    ExportRequest,
    ExportResponse,
    HRAnalyticsResponse,
    PredictiveAnalyticsResponse,
    RecruiterAnalyticsResponse,
    ReportCreateRequest,
    ReportListResponse,
    ReportResponse,
)
from app.domain.models import User
from app.services.analytics.admin_analytics import AdminAnalyticsService
from app.services.analytics.ai_insights import AIInsightsService
from app.services.analytics.candidate_analytics import CandidateAnalyticsService
from app.services.analytics.executive_kpis import ExecutiveKPIsService
from app.services.analytics.hr_analytics import HRAnalyticsService
from app.services.analytics.predictive_analytics import PredictiveAnalyticsService
from app.services.analytics.recruiter_analytics import RecruiterAnalyticsService
from app.services.analytics.report_service import ReportService

router = APIRouter(prefix="/analytics", tags=["analytics"])


# ─── Candidate Analytics ─────────────────────────────────────────────


@router.get("/candidate", response_model=CandidatePerformanceResponse)
async def candidate_analytics(
    current_user: User = Depends(require_role("candidate", "hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = CandidateAnalyticsService(db)
    return await service.get_candidate_performance(current_user.id)


# ─── Recruiter Analytics ─────────────────────────────────────────────


@router.get("/recruiter", response_model=RecruiterAnalyticsResponse)
async def recruiter_analytics(
    current_user: User = Depends(require_role("hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = RecruiterAnalyticsService(db)
    role = current_user.roles[0].role.name if current_user.roles else "recruiter"
    recruiter_id = current_user.id if role == "recruiter" else None
    return await service.get_recruiter_analytics(recruiter_id)


# ─── HR Analytics ────────────────────────────────────────────────────


@router.get("/hr", response_model=HRAnalyticsResponse)
async def hr_analytics(
    current_user: User = Depends(require_role("hr")),
    db: AsyncSession = Depends(get_db),
):
    service = HRAnalyticsService(db)
    return await service.get_hr_analytics()


# ─── Admin Analytics ─────────────────────────────────────────────────


@router.get("/admin", response_model=AdminAnalyticsResponse)
async def admin_analytics(
    current_user: User = Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    service = AdminAnalyticsService(db)
    return await service.get_admin_analytics()


# ─── Executive KPIs ──────────────────────────────────────────────────


@router.get("/executive", response_model=ExecutiveKPIsResponse)
async def executive_kpis(
    current_user: User = Depends(require_role("admin", "hr")),
    db: AsyncSession = Depends(get_db),
):
    service = ExecutiveKPIsService(db)
    return await service.get_executive_kpis()


# ─── Predictive Analytics ────────────────────────────────────────────


@router.get("/predictions", response_model=PredictiveAnalyticsResponse)
async def predictive_analytics(
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = PredictiveAnalyticsService(db)
    return await service.get_predictions()


# ─── AI Insights ─────────────────────────────────────────────────────


@router.get("/insights", response_model=AIInsightsResponse)
async def ai_insights(
    insight_type: str | None = Query(default=None),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = AIInsightsService(db)
    return await service.get_insights(insight_type=insight_type)


# ─── Reports CRUD ────────────────────────────────────────────────────


@router.get("/reports", response_model=ReportListResponse)
async def list_reports(
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.list_reports(current_user.id)


@router.post("/reports", response_model=ReportResponse, status_code=201)
async def create_report(
    body: ReportCreateRequest,
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.create_report(current_user.id, body)


@router.post("/export", response_model=ExportResponse)
async def export_report(
    body: ExportRequest,
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.export_report(body)


# ─── Alert Rules ─────────────────────────────────────────────────────


@router.get("/alerts", response_model=list[AlertRuleResponse])
async def list_alerts(
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.list_alert_rules(current_user.id)


@router.post("/alerts", response_model=AlertRuleResponse, status_code=201)
async def create_alert(
    body: AlertRuleCreateRequest,
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.create_alert_rule(current_user.id, body)


# ─── Dashboard Layout ────────────────────────────────────────────────


@router.get("/dashboard-layout", response_model=DashboardLayoutResponse | None)
async def get_layout(
    dashboard_key: str = Query(...),
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.get_dashboard_layout(current_user.id, dashboard_key)


@router.post("/dashboard-layout", response_model=DashboardLayoutResponse)
async def save_layout(
    body: DashboardLayoutRequest,
    current_user: User = Depends(require_role("admin", "hr", "recruiter")),
    db: AsyncSession = Depends(get_db),
):
    service = ReportService(db)
    return await service.save_dashboard_layout(current_user.id, body)
