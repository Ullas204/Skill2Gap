"""Analytics Repository — queries existing data for analytics computations."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select, case, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics_models import (
    AlertRule,
    AnalyticsInsight,
    AnalyticsReport,
    DashboardLayout,
    ScheduledReport,
)
from app.domain.models import (
    CandidateRanking,
    CodingAssessment,
    Interview,
    InterviewAnswer,
    InterviewQuestion,
    InterviewScorecard,
    Job,
    JobApplication,
    Resume,
    Role,
    ScreeningResult,
    User,
    UserRole,
)


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    # ── User counts ──────────────────────────────────────────────

    async def count_users(self, role: str | None = None) -> int:
        stmt = select(func.count(User.id))
        if role:
            stmt = (
                stmt
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, UserRole.role_id == Role.id)
                .where(Role.name == role)
            )
        result = await self._s.execute(stmt)
        return result.scalar() or 0

    async def count_active_users(self) -> int:
        stmt = select(func.count(User.id)).where(User.is_active.is_(True))
        result = await self._s.execute(stmt)
        return result.scalar() or 0

    async def users_trend(self, days: int = 30) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                func.date(User.created_at).label("date"),
                func.count(User.id).label("count"),
            )
            .where(User.created_at >= cutoff)
            .group_by(func.date(User.created_at))
            .order_by(func.date(User.created_at))
        )
        result = await self._s.execute(stmt)
        return [{"label": str(r.date), "value": r.count} for r in result.all()]

    # ── Job counts ───────────────────────────────────────────────

    async def count_jobs(self, status: str | None = None) -> int:
        stmt = select(func.count(Job.id))
        if status:
            stmt = stmt.where(Job.status == status)
        result = await self._s.execute(stmt)
        return result.scalar() or 0

    async def jobs_by_status(self) -> list[dict]:
        stmt = (
            select(Job.status, func.count(Job.id).label("count"))
            .group_by(Job.status)
        )
        result = await self._s.execute(stmt)
        return [{"status": r.status, "count": r.count} for r in result.all()]

    # ── Application counts ───────────────────────────────────────

    async def count_applications(self, candidate_id: uuid.UUID | None = None) -> int:
        stmt = select(func.count(JobApplication.id))
        if candidate_id:
            stmt = stmt.where(JobApplication.candidate_id == candidate_id)
        result = await self._s.execute(stmt)
        return result.scalar() or 0

    async def applications_by_status(self, candidate_id: uuid.UUID | None = None) -> list[dict]:
        stmt = select(JobApplication.status, func.count(JobApplication.id).label("count"))
        if candidate_id:
            stmt = stmt.where(JobApplication.candidate_id == candidate_id)
        stmt = stmt.group_by(JobApplication.status)
        result = await self._s.execute(stmt)
        return [{"status": r.status, "count": r.count} for r in result.all()]

    async def applications_trend(self, days: int = 30) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                func.date(JobApplication.created_at).label("date"),
                func.count(JobApplication.id).label("count"),
            )
            .where(JobApplication.created_at >= cutoff)
            .group_by(func.date(JobApplication.created_at))
            .order_by(func.date(JobApplication.created_at))
        )
        result = await self._s.execute(stmt)
        return [{"label": str(r.date), "value": r.count} for r in result.all()]

    # ── Screening ────────────────────────────────────────────────

    async def avg_screening_score(self) -> float:
        stmt = select(func.avg(ScreeningResult.overall_match_score))
        result = await self._s.execute(stmt)
        return round(result.scalar() or 0.0, 2)

    async def top_screened_candidates(self, limit: int = 10) -> list[dict]:
        stmt = (
            select(
                ScreeningResult.candidate_id,
                func.avg(ScreeningResult.overall_match_score).label("avg_score"),
            )
            .group_by(ScreeningResult.candidate_id)
            .order_by(func.avg(ScreeningResult.ai_score).desc())
            .limit(limit)
        )
        result = await self._s.execute(stmt)
        return [{"candidate_id": str(r.candidate_id), "value": r.avg_score} for r in result.all()]

    # ── Interviews ───────────────────────────────────────────────

    async def count_interviews(self, status: str | None = None, recruiter_id: uuid.UUID | None = None) -> int:
        stmt = select(func.count(Interview.id))
        if status:
            stmt = stmt.where(Interview.status == status)
        if recruiter_id:
            stmt = stmt.where(Interview.recruiter_id == recruiter_id)
        result = await self._s.execute(stmt)
        return result.scalar() or 0

    async def avg_interview_score(self) -> float:
        stmt = select(func.avg(InterviewScorecard.overall_score))
        result = await self._s.execute(stmt)
        return round(result.scalar() or 0.0, 2)

    async def interviews_by_status(self) -> list[dict]:
        stmt = (
            select(Interview.status, func.count(Interview.id).label("count"))
            .group_by(Interview.status)
        )
        result = await self._s.execute(stmt)
        return [{"status": r.status, "count": r.count} for r in result.all()]

    async def interviews_trend(self, days: int = 30) -> list[dict]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        stmt = (
            select(
                func.date(Interview.created_at).label("date"),
                func.count(Interview.id).label("count"),
            )
            .where(Interview.created_at >= cutoff)
            .group_by(func.date(Interview.created_at))
            .order_by(func.date(Interview.created_at))
        )
        result = await self._s.execute(stmt)
        return [{"label": str(r.date), "value": r.count} for r in result.all()]

    # ── Resume counts ────────────────────────────────────────────

    async def count_resumes(self) -> int:
        stmt = select(func.count(Resume.id))
        result = await self._s.execute(stmt)
        return result.scalar() or 0

    # ── Resumes by user ──────────────────────────────────────────

    async def count_resumes_by_user(self, user_id: uuid.UUID) -> int:
        stmt = select(func.count(Resume.id)).where(Resume.user_id == user_id)
        result = await self._s.execute(stmt)
        return result.scalar() or 0

    # ── Ranking ──────────────────────────────────────────────────

    async def count_rankings(self) -> int:
        stmt = select(func.count(CandidateRanking.id))
        result = await self._s.execute(stmt)
        return result.scalar() or 0

    # ── Coding assessments ───────────────────────────────────────

    async def coding_avg_score(self) -> float:
        stmt = select(func.avg(CodingAssessment.score))
        result = await self._s.execute(stmt)
        return round(result.scalar() or 0.0, 2)

    # ── Reports ──────────────────────────────────────────────────

    async def list_reports(self, user_id: uuid.UUID) -> list[AnalyticsReport]:
        stmt = (
            select(AnalyticsReport)
            .where(AnalyticsReport.user_id == user_id)
            .order_by(AnalyticsReport.created_at.desc())
        )
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    async def create_report(self, **kwargs) -> AnalyticsReport:
        report = AnalyticsReport(**kwargs)
        self._s.add(report)
        await self._s.flush()
        return report

    async def get_report(self, report_id: uuid.UUID) -> AnalyticsReport | None:
        stmt = select(AnalyticsReport).where(AnalyticsReport.id == report_id)
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    # ── Alert Rules ──────────────────────────────────────────────

    async def list_alert_rules(self, user_id: uuid.UUID) -> list[AlertRule]:
        stmt = (
            select(AlertRule)
            .where(AlertRule.user_id == user_id)
            .order_by(AlertRule.created_at.desc())
        )
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    async def create_alert_rule(self, **kwargs) -> AlertRule:
        rule = AlertRule(**kwargs)
        self._s.add(rule)
        await self._s.flush()
        return rule

    # ── Dashboard Layout ─────────────────────────────────────────

    async def get_dashboard_layout(self, user_id: uuid.UUID, dashboard_key: str) -> DashboardLayout | None:
        stmt = select(DashboardLayout).where(
            DashboardLayout.user_id == user_id,
            DashboardLayout.dashboard_key == dashboard_key,
        )
        result = await self._s.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_dashboard_layout(self, user_id: uuid.UUID, dashboard_key: str, layout_config: dict) -> DashboardLayout:
        existing = await self.get_dashboard_layout(user_id, dashboard_key)
        if existing:
            existing.layout_config = layout_config
            await self._s.flush()
            return existing
        layout = DashboardLayout(user_id=user_id, dashboard_key=dashboard_key, layout_config=layout_config)
        self._s.add(layout)
        await self._s.flush()
        return layout

    # ── Insights ─────────────────────────────────────────────────

    async def list_insights(self, insight_type: str | None = None, limit: int = 50) -> list[AnalyticsInsight]:
        stmt = select(AnalyticsInsight).where(AnalyticsInsight.is_active.is_(True))
        if insight_type:
            stmt = stmt.where(AnalyticsInsight.insight_type == insight_type)
        stmt = stmt.order_by(AnalyticsInsight.priority.desc()).limit(limit)
        result = await self._s.execute(stmt)
        return list(result.scalars().all())

    async def create_insight(self, **kwargs) -> AnalyticsInsight:
        insight = AnalyticsInsight(**kwargs)
        self._s.add(insight)
        await self._s.flush()
        return insight

    # ── Scheduled Reports ────────────────────────────────────────

    async def list_scheduled_reports(self, user_id: uuid.UUID) -> list[ScheduledReport]:
        stmt = (
            select(ScheduledReport)
            .where(ScheduledReport.user_id == user_id)
            .order_by(ScheduledReport.created_at.desc())
        )
        result = await self._s.execute(stmt)
        return list(result.scalars().all())
