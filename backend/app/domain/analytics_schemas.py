import uuid
from datetime import datetime
from pydantic import BaseModel, Field


# ─── Common ──────────────────────────────────────────────────────────


class TimeRangeRequest(BaseModel):
    start_date: datetime | None = None
    end_date: datetime | None = None
    period: str = Field(default="30d", pattern="^(7d|30d|90d|1y|all)$")


class KPIMetric(BaseModel):
    label: str
    value: float
    unit: str = ""
    change_pct: float = 0.0
    trend: str = "stable"
    icon: str | None = None


class ChartDataPoint(BaseModel):
    label: str
    value: float
    secondary_value: float | None = None
    color: str | None = None


class ChartDataset(BaseModel):
    label: str
    data: list[float]
    color: str | None = None


class ChartData(BaseModel):
    labels: list[str]
    datasets: list[ChartDataset]


class DataDistribution(BaseModel):
    label: str
    count: int
    percentage: float


class StatusBreakdown(BaseModel):
    status: str
    count: int
    percentage: float


# ─── Candidate Analytics ─────────────────────────────────────────────


class CandidatePerformanceResponse(BaseModel):
    overall_score: float
    skill_match_pct: float
    interview_avg_score: float
    resume_score: float
    application_count: int
    interview_count: int
    strongest_skills: list[DataDistribution]
    score_trend: ChartData
    applications_by_status: list[StatusBreakdown]
    improvement_areas: list[str]
    rank_percentile: float


# ─── Recruiter Analytics ─────────────────────────────────────────────


class RecruiterAnalyticsResponse(BaseModel):
    total_jobs: int
    active_jobs: int
    total_applicants: int
    avg_time_to_fill: float
    avg_time_to_screen: float
    hire_rate: float
    jobs_by_status: list[StatusBreakdown]
    applicants_trend: ChartData
    top_jobs: list[ChartDataPoint]
    source_effectiveness: list[DataDistribution]
    pipeline_velocity: list[ChartDataPoint]


# ─── HR Analytics ────────────────────────────────────────────────────


class HRAnalyticsResponse(BaseModel):
    total_headcount: int
    open_positions: int
    avg_time_to_hire: float
    acceptance_rate: float
    diversity_index: float
    turnover_rate: float
    headcount_trend: ChartData
    department_distribution: list[DataDistribution]
    gender_distribution: list[DataDistribution]
    hiring_funnel: list[StatusBreakdown]
    recruiter_performance: list[ChartDataPoint]


# ─── Admin Analytics ─────────────────────────────────────────────────


class AdminAnalyticsResponse(BaseModel):
    total_users: int
    active_users: int
    total_jobs: int
    total_applications: int
    system_health_score: float
    storage_used_mb: float
    api_calls_today: int
    users_by_role: list[DataDistribution]
    users_trend: ChartData
    security_events: list[ChartDataPoint]
    system_load: list[ChartDataPoint]


# ─── Executive KPIs ──────────────────────────────────────────────────


class ExecutiveKPIsResponse(BaseModel):
    revenue_per_hire: float
    cost_per_hire: float
    quality_of_hire: float
    time_to_productivity: float
    hiring_forecast: ChartData
    department_kpis: list[ChartDataPoint]
    quarterly_trends: ChartData
    risk_indicators: list[DataDistribution]


# ─── Predictive Analytics ────────────────────────────────────────────


class PredictiveAnalyticsResponse(BaseModel):
    demand_forecast: ChartData
    attrition_risk: list[ChartDataPoint]
    skill_gap_forecast: list[DataDistribution]
    hiring_timeline: ChartData
    budget_projection: ChartData
    confidence_score: float
    recommendations: list[str]


# ─── AI Insights ─────────────────────────────────────────────────────


class AIInsightItem(BaseModel):
    id: uuid.UUID
    insight_type: str
    title: str
    summary: str
    data_payload: dict | None = None
    priority: int
    created_at: datetime


class AIInsightsResponse(BaseModel):
    insights: list[AIInsightItem]
    total: int
    categories: list[DataDistribution]


# ─── Reports ─────────────────────────────────────────────────────────


class ReportCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    report_type: str = Field(..., pattern="^(candidate|recruiter|hr|admin|executive)$")
    config: dict | None = None
    is_scheduled: bool = False
    schedule_cron: str | None = None


class ReportResponse(BaseModel):
    id: uuid.UUID
    title: str
    report_type: str
    config: dict | None
    is_scheduled: bool
    schedule_cron: str | None
    last_generated_at: datetime | None
    created_at: datetime


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int


class ExportRequest(BaseModel):
    report_type: str = Field(..., pattern="^(candidate|recruiter|hr|admin|executive)$")
    format: str = Field(default="pdf", pattern="^(pdf|excel|csv)$")
    filters: dict | None = None


class ExportResponse(BaseModel):
    download_url: str
    format: str
    generated_at: datetime


# ─── Alert Rules ─────────────────────────────────────────────────────


class AlertRuleCreateRequest(BaseModel):
    alert_type: str = Field(..., pattern="^(hiring_delay|low_volume|bias_warning|security_event|system_health|schedule_conflict|job_expiring)$")
    title: str = Field(..., min_length=1, max_length=255)
    condition_config: dict
    threshold: int | None = None


class AlertRuleResponse(BaseModel):
    id: uuid.UUID
    alert_type: str
    title: str
    condition_config: dict
    is_active: bool
    threshold: int | None
    last_triggered_at: datetime | None
    created_at: datetime


# ─── Dashboard Layout ────────────────────────────────────────────────


class DashboardLayoutRequest(BaseModel):
    dashboard_key: str = Field(..., min_length=1, max_length=100)
    layout_config: dict


class DashboardLayoutResponse(BaseModel):
    id: uuid.UUID
    dashboard_key: str
    layout_config: dict
    created_at: datetime
