"""Audit logging service for security-sensitive operations."""
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.enums import AuditEventType
from app.repositories.audit_log import AuditLogRepository

logger = get_logger(__name__)


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuditLogRepository(session)

    async def log(
        self,
        event_type: str | AuditEventType,
        action: str,
        user_id: uuid.UUID | None = None,
        organization_id: uuid.UUID | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        success: bool = True,
    ) -> None:
        event_str = event_type.value if isinstance(event_type, AuditEventType) else event_type
        await self._repo.log_event(
            event_type=event_str,
            action=action,
            user_id=user_id,
            organization_id=organization_id,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
            success=success,
        )
        logger.info("Audit: event=%s action=%s user=%s org=%s success=%s",
                     event_str, action, user_id, organization_id, success)

    async def log_login(self, user_id: uuid.UUID, ip: str | None = None, ua: str | None = None) -> None:
        await self.log(AuditEventType.LOGIN, "user_login", user_id=user_id, ip_address=ip, user_agent=ua)

    async def log_login_failed(self, email: str, ip: str | None = None, reason: str = "invalid_credentials") -> None:
        await self.log(AuditEventType.LOGIN_FAILED, "login_failed", details={"email": email, "reason": reason}, ip_address=ip, success=False)

    async def log_logout(self, user_id: uuid.UUID, ip: str | None = None) -> None:
        await self.log(AuditEventType.LOGOUT, "user_logout", user_id=user_id, ip_address=ip)

    async def log_register(self, user_id: uuid.UUID, email: str, role: str, ip: str | None = None) -> None:
        await self.log(AuditEventType.REGISTER, "user_register", user_id=user_id, details={"email": email, "role": role}, ip_address=ip)

    async def log_invitation_created(self, user_id: uuid.UUID, org_id: uuid.UUID, invite_email: str, role: str) -> None:
        await self.log(AuditEventType.INVITATION_CREATED, "invitation_create", user_id=user_id, organization_id=org_id, details={"invite_email": invite_email, "role": role})

    async def log_invitation_accepted(self, user_id: uuid.UUID, org_id: uuid.UUID) -> None:
        await self.log(AuditEventType.INVITATION_ACCEPTED, "invitation_accept", user_id=user_id, organization_id=org_id)

    async def log_membership_change(self, user_id: uuid.UUID, org_id: uuid.UUID, action: str, target_user: uuid.UUID | None = None, details: dict | None = None) -> None:
        d = details or {}
        if target_user:
            d["target_user_id"] = str(target_user)
        await self.log(AuditEventType.MEMBERSHIP_SUSPENDED, action, user_id=user_id, organization_id=org_id, details=d)

    async def log_auth_failure(self, user_id: uuid.UUID | None, reason: str, path: str, ip: str | None = None) -> None:
        await self.log(AuditEventType.AUTHORIZATION_FAILURE, "auth_failure", user_id=user_id, details={"reason": reason, "path": path}, ip_address=ip, success=False)
