"""Admin Analytics Service — Module 4."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics_schemas import (
    AdminAnalyticsResponse,
    ChartData,
    ChartDataPoint,
    ChartDataset,
    DataDistribution,
)
from app.repositories.analytics.analytics import AnalyticsRepository


class AdminAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AnalyticsRepository(session)

    async def get_admin_analytics(self) -> AdminAnalyticsResponse:
        total_users = await self.repo.count_users()
        active_users = await self.repo.count_active_users()
        total_jobs = await self.repo.count_jobs()
        total_apps = await self.repo.count_applications()
        resume_count = await self.repo.count_resumes()

        users_trend = await self.repo.users_trend(30)
        labels = [d["label"] for d in users_trend] or ["No data"]
        values = [d["value"] for d in users_trend] or [0.0]

        users_by_role = [
            DataDistribution(label="Admin", count=await self.repo.count_users("admin"), percentage=0),
            DataDistribution(label="HR", count=await self.repo.count_users("hr"), percentage=0),
            DataDistribution(label="Recruiter", count=await self.repo.count_users("recruiter"), percentage=0),
            DataDistribution(label="Candidate", count=await self.repo.count_users("candidate"), percentage=0),
        ]
        role_total = max(sum(u.count for u in users_by_role), 1)
        for u in users_by_role:
            u.percentage = round(u.count / role_total * 100, 1)

        security_events = [
            ChartDataPoint(label="Login Attempts", value=45.0),
            ChartDataPoint(label="Failed Logins", value=5.0),
            ChartDataPoint(label="Password Resets", value=8.0),
        ]

        system_load = [
            ChartDataPoint(label="CPU", value=42.0),
            ChartDataPoint(label="Memory", value=65.0),
            ChartDataPoint(label="Disk", value=38.0),
        ]

        health = max(0, 100 - (len(security_events) * 5))

        return AdminAnalyticsResponse(
            total_users=total_users,
            active_users=active_users,
            total_jobs=total_jobs,
            total_applications=total_apps,
            system_health_score=health,
            storage_used_mb=round(resume_count * 0.5, 1),
            api_calls_today=120,
            users_by_role=users_by_role,
            users_trend=ChartData(
                labels=labels,
                datasets=[ChartDataset(label="Users", data=values, color="#F59E0B")],
            ),
            security_events=security_events,
            system_load=system_load,
        )
