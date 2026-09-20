import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.domain.enums import AlertType, ExportFormat, InsightCategory, ReportType


class AnalyticsReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "analytics_reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    report_type: Mapped[ReportType] = mapped_column(String(30), nullable=False)
    config: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    is_scheduled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    schedule_cron: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_generated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User")


class DashboardLayout(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "dashboard_layouts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    dashboard_key: Mapped[str] = mapped_column(String(100), nullable=False)
    layout_config: Mapped[dict] = mapped_column(JSON, nullable=False)

    user: Mapped["User"] = relationship("User")


class AlertRule(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "alert_rules"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    alert_type: Mapped[AlertType] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    condition_config: Mapped[dict] = mapped_column(JSON, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    threshold: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_triggered_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User")


class ScheduledReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "scheduled_reports"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    report_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("analytics_reports.id", ondelete="SET NULL"), nullable=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    export_format: Mapped[ExportFormat] = mapped_column(String(20), nullable=False)
    recipients: Mapped[list | None] = mapped_column(JSON, nullable=True)
    frequency: Mapped[str] = mapped_column(String(50), nullable=False)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User"] = relationship("User")


class AnalyticsInsight(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "analytics_insights"

    insight_type: Mapped[InsightCategory] = mapped_column(String(30), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    data_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    target_roles: Mapped[list | None] = mapped_column(JSON, nullable=True)
