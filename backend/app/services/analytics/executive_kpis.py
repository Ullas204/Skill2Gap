"""Executive KPIs Service — Module 5."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics_schemas import (
    ChartData,
    ChartDataPoint,
    ChartDataset,
    DataDistribution,
    ExecutiveKPIsResponse,
)
from app.repositories.analytics.analytics import AnalyticsRepository


class ExecutiveKPIsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AnalyticsRepository(session)

    async def get_executive_kpis(self) -> ExecutiveKPIsResponse:
        total_apps = await self.repo.count_applications()
        total_jobs = await self.repo.count_jobs()
        total_users = await self.repo.count_users()
        avg_score = await self.repo.avg_screening_score()

        cost_per_hire = 4500.0
        revenue_per_hire = 75000.0
        quality_of_hire = avg_score if avg_score else 72.0

        dept_kpis = [
            ChartDataPoint(label="Engineering", value=85.0),
            ChartDataPoint(label="Sales", value=78.0),
            ChartDataPoint(label="Marketing", value=72.0),
            ChartDataPoint(label="Operations", value=68.0),
        ]

        quarterly = ChartData(
            labels=["Q1", "Q2", "Q3", "Q4"],
            datasets=[
                ChartDataset(label="Hires", data=[12.0, 18.0, 15.0, 22.0], color="#10B981"),
                ChartDataset(label="Revenue", data=[50.0, 62.0, 55.0, 70.0], color="#3B82F6"),
            ],
        )

        hiring_forecast = ChartData(
            labels=["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"],
            datasets=[
                ChartDataset(
                    label="Forecasted Hires",
                    data=[8.0, 10.0, 12.0, 11.0, 14.0, 16.0],
                    color="#8B5CF6",
                ),
            ],
        )

        risk_indicators = [
            DataDistribution(label="Low", count=3, percentage=60.0),
            DataDistribution(label="Medium", count=1, percentage=20.0),
            DataDistribution(label="High", count=1, percentage=20.0),
        ]

        return ExecutiveKPIsResponse(
            revenue_per_hire=revenue_per_hire,
            cost_per_hire=cost_per_hire,
            quality_of_hire=quality_of_hire,
            time_to_productivity=45.0,
            hiring_forecast=hiring_forecast,
            department_kpis=dept_kpis,
            quarterly_trends=quarterly,
            risk_indicators=risk_indicators,
        )
