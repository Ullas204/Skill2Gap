"""Audit log repository for security event tracking."""
import uuid
from typing import Any

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import AuditLog
from app.repositories.base import BaseRepository


class AuditLogRepository(BaseRepository[AuditLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AuditLog)

    async def log_event(
        self,
        event_type: str,
        action: str,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
    ) -> AuditLog:
        log = AuditLog(
            user_id=user_id,
            organization_id=organization_id,
            event_type=event_type,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
        )
        self._session.add(log)
        await self._session.flush()
        return log

    async def get_user_events(
        self, user_id: uuid.UUID, limit: int = 50
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.user_id == user_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_org_events(
        self, organization_id: uuid.UUID, limit: int = 100
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.organization_id == organization_id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_event_type(
        self, event_type: str, limit: int = 100
    ) -> list[AuditLog]:
        stmt = (
            select(AuditLog)
            .where(AuditLog.event_type == event_type)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
