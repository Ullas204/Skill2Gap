import uuid

from fastapi import APIRouter, Depends, Path

from app.api.deps import get_current_user, get_user_service, require_role
from app.domain.models import User
from app.domain.schemas import MessageResponse, UserResponse, UserUpdate
from app.services.user import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
async def list_users(
    service: UserService = Depends(get_user_service),
    _: User = Depends(require_role("admin")),
):
    return await service.list_users()


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: uuid.UUID = Path(...),
    service: UserService = Depends(get_user_service),
    _: User = Depends(require_role("admin", "hr")),
):
    return await service.get_user(user_id)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    body: UserUpdate,
    user_id: uuid.UUID = Path(...),
    service: UserService = Depends(get_user_service),
    _: User = Depends(require_role("admin")),
):
    kwargs = body.model_dump(exclude_unset=True)
    return await service.update_user(user_id, **kwargs)


@router.delete("/{user_id}", response_model=MessageResponse)
async def delete_user(
    user_id: uuid.UUID = Path(...),
    service: UserService = Depends(get_user_service),
    _: User = Depends(require_role("admin")),
):
    await service.delete_user(user_id)
    return MessageResponse(message="User deleted")


@router.post("/{user_id}/roles/{role_name}", response_model=UserResponse)
async def assign_role(
    user_id: uuid.UUID = Path(...),
    role_name: str = Path(...),
    service: UserService = Depends(get_user_service),
    _: User = Depends(require_role("admin")),
):
    return await service.assign_role(user_id, role_name)


@router.delete("/{user_id}/roles/{role_name}", response_model=UserResponse)
async def remove_role(
    user_id: uuid.UUID = Path(...),
    role_name: str = Path(...),
    service: UserService = Depends(get_user_service),
    _: User = Depends(require_role("admin")),
):
    return await service.remove_role(user_id, role_name)
