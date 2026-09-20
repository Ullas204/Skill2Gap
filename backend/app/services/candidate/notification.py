import uuid

from app.core.exceptions import NotFoundError
from app.domain.candidate_schemas import NotificationResponse
from app.repositories.candidate.notification import NotificationRepository


class NotificationService:
    def __init__(self, notification_repo: NotificationRepository) -> None:
        self._notification_repo = notification_repo

    async def list_notifications(self, user_id: uuid.UUID) -> list[NotificationResponse]:
        notifications = await self._notification_repo.list_by_user(user_id)
        return [NotificationResponse.model_validate(n) for n in notifications]

    async def mark_read(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> NotificationResponse:
        notification = await self._notification_repo.mark_as_read(notification_id, user_id)
        if not notification:
            raise NotFoundError(detail="Notification not found")
        return NotificationResponse.model_validate(notification)

    async def mark_all_read(self, user_id: uuid.UUID) -> None:
        await self._notification_repo.mark_all_as_read(user_id)

    async def delete_notification(self, user_id: uuid.UUID, notification_id: uuid.UUID) -> None:
        notification = await self._notification_repo.get(notification_id)
        if not notification or notification.user_id != user_id:
            raise NotFoundError(detail="Notification not found")
        await self._notification_repo.delete(notification_id)

    async def get_unread_count(self, user_id: uuid.UUID) -> int:
        return await self._notification_repo.count_unread(user_id)
