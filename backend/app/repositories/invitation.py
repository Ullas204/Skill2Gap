"""Invitation repository for secure team onboarding."""
import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Invitation
from app.domain.enums import InvitationStatus
from app.repositories.base import BaseRepository


class InvitationRepository(BaseRepository[Invitation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Invitation)

    async def get_by_token_hash(self, token_hash: str) -> Invitation | None:
        stmt = select(Invitation).where(Invitation.token_hash == token_hash)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_pending_by_email_and_org(
        self, email: str, organization_id: uuid.UUID
    ) -> Invitation | None:
        stmt = select(Invitation).where(
            Invitation.email == email,
            Invitation.organization_id == organization_id,
            Invitation.status == InvitationStatus.PENDING.value,
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_org_invitations(
        self, organization_id: uuid.UUID, include_expired: bool = False
    ) -> list[Invitation]:
        stmt = select(Invitation).where(
            Invitation.organization_id == organization_id
        )
        if not include_expired:
            stmt = stmt.where(
                Invitation.status.in_([
                    InvitationStatus.PENDING.value,
                    InvitationStatus.ACCEPTED.value,
                ])
            )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def revoke(self, invitation_id: uuid.UUID) -> bool:
        invitation = await self.get(invitation_id)
        if invitation and invitation.status == InvitationStatus.PENDING.value:
            invitation.status = InvitationStatus.REVOKED.value
            await self._session.flush()
            return True
        return False

    async def mark_accepted(self, invitation_id: uuid.UUID, accepted_by_id: uuid.UUID) -> None:
        invitation = await self.get(invitation_id)
        if invitation:
            invitation.status = InvitationStatus.ACCEPTED.value
            invitation.accepted_by_id = accepted_by_id
            from datetime import datetime, timezone
            invitation.accepted_at = datetime.now(timezone.utc)
            await self._session.flush()

    async def mark_accepted_if_pending(
        self, invitation_id: uuid.UUID, accepted_by_id: uuid.UUID
    ) -> bool:
        """Atomically consume a pending invitation.

        Uses a conditional UPDATE so only one concurrent request can transition
        the invitation from pending → accepted. Returns False when another
        request already consumed (or revoked/expired) it.
        """
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        stmt = (
            update(Invitation)
            .where(
                Invitation.id == invitation_id,
                Invitation.status == InvitationStatus.PENDING.value,
            )
            .values(
                status=InvitationStatus.ACCEPTED.value,
                accepted_by_id=accepted_by_id,
                accepted_at=now,
            )
        )
        result = await self._session.execute(stmt)
        return bool(result.rowcount and result.rowcount > 0)
