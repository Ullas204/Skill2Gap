import uuid

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Notification
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Notification)

    async def list_by_user(self, user_id: uuid.UUID) -> list[Notification]:
        stmt = select(Notification).where(Notification.user_id == user_id).order_by(Notification.created_at.desc())
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def mark_as_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> Notification | None:
        stmt = (
            update(Notification)
            .where(Notification.id == notification_id, Notification.user_id == user_id)
            .values(is_read=True)
            .returning(Notification)
        )
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.scalar_one_or_none()

    async def mark_all_as_read(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.is_read == False)
            .values(is_read=True)
        )
        await self._session.execute(stmt)
        await self._session.flush()

    async def count_unread(self, user_id: uuid.UUID) -> int:
        stmt = select(Notification).where(Notification.user_id == user_id, Notification.is_read == False)
        result = await self._session.execute(stmt)
        return len(result.scalars().all())

    async def create_welcome_notification(self, user_id: uuid.UUID) -> Notification:
        return await self.create(
            user_id=user_id,
            title="Welcome to AI Hiring Copilot",
            message="Your candidate portal is ready. Complete your profile to get started.",
            notification_type="welcome",
        )
