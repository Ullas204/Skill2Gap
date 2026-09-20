import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.domain.candidate_schemas import NotificationResponse
from app.domain.models import User
from app.domain.schemas import MessageResponse
from app.repositories.candidate.notification import NotificationRepository
from app.services.candidate.notification import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _get_service(db: AsyncSession = Depends(get_db)) -> NotificationService:
    return NotificationService(NotificationRepository(db))


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    service: NotificationService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
):
    return await service.list_notifications(current_user.id)


@router.get("/unread-count")
async def unread_count(
    service: NotificationService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
):
    count = await service.get_unread_count(current_user.id)
    return {"count": count}


@router.put("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: uuid.UUID,
    service: NotificationService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
):
    try:
        return await service.mark_read(current_user.id, notification_id)
    except Exception:
        raise HTTPException(status_code=404, detail="Notification not found")


@router.put("/read-all", response_model=MessageResponse)
async def mark_all_read(
    service: NotificationService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
):
    await service.mark_all_read(current_user.id)
    return MessageResponse(message="All notifications marked as read")


@router.delete("/{notification_id}", response_model=MessageResponse)
async def delete_notification(
    notification_id: uuid.UUID,
    service: NotificationService = Depends(_get_service),
    current_user: User = Depends(get_current_user),
):
    try:
        await service.delete_notification(current_user.id, notification_id)
        return MessageResponse(message="Notification deleted")
    except Exception:
        raise HTTPException(status_code=404, detail="Notification not found")
