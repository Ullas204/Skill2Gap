"""Report Service — Module 8."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.analytics_schemas import (
    ExportRequest,
    ExportResponse,
    ReportCreateRequest,
    ReportResponse,
    ReportListResponse,
    AlertRuleCreateRequest,
    AlertRuleResponse,
    DashboardLayoutRequest,
    DashboardLayoutResponse,
)
from app.repositories.analytics.analytics import AnalyticsRepository


class ReportService:
    def __init__(self, session: AsyncSession) -> None:
        self.repo = AnalyticsRepository(session)

    # ── Reports ──────────────────────────────────────────────────

    async def list_reports(self, user_id: uuid.UUID) -> ReportListResponse:
        reports = await self.repo.list_reports(user_id)
        items = [
            ReportResponse(
                id=r.id,
                title=r.title,
                report_type=r.report_type,
                config=r.config,
                is_scheduled=r.is_scheduled,
                schedule_cron=r.schedule_cron,
                last_generated_at=r.last_generated_at,
                created_at=r.created_at,
            )
            for r in reports
        ]
        return ReportListResponse(reports=items, total=len(items))

    async def create_report(self, user_id: uuid.UUID, data: ReportCreateRequest) -> ReportResponse:
        report = await self.repo.create_report(
            user_id=user_id,
            title=data.title,
            report_type=data.report_type,
            config=data.config,
            is_scheduled=data.is_scheduled,
            schedule_cron=data.schedule_cron,
        )
        return ReportResponse(
            id=report.id,
            title=report.title,
            report_type=report.report_type,
            config=report.config,
            is_scheduled=report.is_scheduled,
            schedule_cron=report.schedule_cron,
            last_generated_at=report.last_generated_at,
            created_at=report.created_at,
        )

    # ── Export ───────────────────────────────────────────────────

    async def export_report(self, data: ExportRequest) -> ExportResponse:
        return ExportResponse(
            download_url=f"/uploads/reports/export_{uuid.uuid4().hex[:8]}.{data.format}",
            format=data.format,
            generated_at=datetime.now(timezone.utc),
        )

    # ── Alert Rules ──────────────────────────────────────────────

    async def list_alert_rules(self, user_id: uuid.UUID) -> list[AlertRuleResponse]:
        rules = await self.repo.list_alert_rules(user_id)
        return [
            AlertRuleResponse(
                id=r.id,
                alert_type=r.alert_type,
                title=r.title,
                condition_config=r.condition_config,
                is_active=r.is_active,
                threshold=r.threshold,
                last_triggered_at=r.last_triggered_at,
                created_at=r.created_at,
            )
            for r in rules
        ]

    async def create_alert_rule(self, user_id: uuid.UUID, data: AlertRuleCreateRequest) -> AlertRuleResponse:
        rule = await self.repo.create_alert_rule(
            user_id=user_id,
            alert_type=data.alert_type,
            title=data.title,
            condition_config=data.condition_config,
            threshold=data.threshold,
        )
        return AlertRuleResponse(
            id=rule.id,
            alert_type=rule.alert_type,
            title=rule.title,
            condition_config=rule.condition_config,
            is_active=rule.is_active,
            threshold=rule.threshold,
            last_triggered_at=rule.last_triggered_at,
            created_at=rule.created_at,
        )

    # ── Dashboard Layout ─────────────────────────────────────────

    async def get_dashboard_layout(self, user_id: uuid.UUID, dashboard_key: str) -> DashboardLayoutResponse | None:
        layout = await self.repo.get_dashboard_layout(user_id, dashboard_key)
        if not layout:
            return None
        return DashboardLayoutResponse(
            id=layout.id,
            dashboard_key=layout.dashboard_key,
            layout_config=layout.layout_config,
            created_at=layout.created_at,
        )

    async def save_dashboard_layout(self, user_id: uuid.UUID, data: DashboardLayoutRequest) -> DashboardLayoutResponse:
        layout = await self.repo.upsert_dashboard_layout(
            user_id=user_id,
            dashboard_key=data.dashboard_key,
            layout_config=data.layout_config,
        )
        return DashboardLayoutResponse(
            id=layout.id,
            dashboard_key=layout.dashboard_key,
            layout_config=layout.layout_config,
            created_at=layout.created_at,
        )
