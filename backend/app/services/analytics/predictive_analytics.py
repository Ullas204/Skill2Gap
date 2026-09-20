"""Predictive Analytics Service — Module 6 — rule-based heuristics."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics_schemas import (
    ChartData,
    ChartDataPoint,
    ChartDataset,
    DataDistribution,
    PredictiveAnalyticsResponse,
)
from app.repositories.analytics.analytics import AnalyticsRepository


class PredictiveAnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AnalyticsRepository(session)

    async def get_predictions(self) -> PredictiveAnalyticsResponse:
        total_jobs = await self.repo.count_jobs("published")
        total_apps = await self.repo.count_applications()
        avg_score = await self.repo.avg_screening_score()

        base_hires = max(1, total_jobs * 2)
        demand_data = [float(base_hires + i * 2) for i in range(6)]
        attrition_risk = [
            ChartDataPoint(label="Engineering", value=min(80.0, avg_score * 0.8) if avg_score else 25.0),
            ChartDataPoint(label="Sales", value=min(70.0, avg_score * 0.7) if avg_score else 35.0),
            ChartDataPoint(label="Marketing", value=20.0),
        ]

        skill_gap = [
            DataDistribution(label="Python", count=max(0, 10 - total_jobs), percentage=40.0),
            DataDistribution(label="React", count=max(0, 8 - total_jobs), percentage=30.0),
            DataDistribution(label="SQL", count=max(0, 6 - total_jobs), percentage=20.0),
        ]

        timeline = ChartData(
            labels=["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"],
            datasets=[
                ChartDataset(
                    label="Projected Applications",
                    data=[float(total_apps + i * 5) for i in range(6)],
                    color="#EC4899",
                ),
            ],
        )

        budget = ChartData(
            labels=["Q1", "Q2", "Q3", "Q4"],
            datasets=[
                ChartDataset(label="Budget", data=[50000.0, 60000.0, 55000.0, 70000.0], color="#F59E0B"),
                ChartDataset(label="Actual", data=[45000.0, 58000.0, 0.0, 0.0], color="#EF4444"),
            ],
        )

        return PredictiveAnalyticsResponse(
            demand_forecast=ChartData(
                labels=["Month 1", "Month 2", "Month 3", "Month 4", "Month 5", "Month 6"],
                datasets=[ChartDataset(label="Demand", data=demand_data, color="#10B981")],
            ),
            attrition_risk=attrition_risk,
            skill_gap_forecast=skill_gap,
            hiring_timeline=timeline,
            budget_projection=budget,
            confidence_score=min(85.0, 50.0 + total_apps * 0.1),
            recommendations=[
                "Increase Python hiring efforts",
                "Focus on referral programs to reduce cost-per-hire",
                "Review compensation packages for high-attrition departments",
            ],
        )
