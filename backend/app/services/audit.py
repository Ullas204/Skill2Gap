"""Audit logging service for tracking security events."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.models import AuditLog

logger = get_logger(__name__)


async def log_audit_event(
    session: AsyncSession,
    *,
    user_id: uuid.UUID | None = None,
    event_type: str | None = None,
    action: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    details: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    success: bool = True,
) -> AuditLog:
    audit = AuditLog(
        user_id=user_id,
        event_type=event_type or action.split(".", 1)[0],
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        success=success,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    session.add(audit)
    await session.flush()
    logger.info(
        "Audit: %s user=%s resource=%s/%s success=%s",
        action,
        user_id,
        resource_type,
        resource_id,
        success,
    )
    return audit
