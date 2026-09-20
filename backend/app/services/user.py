import uuid

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.schemas import UserResponse
from app.repositories.user import UserRepository

logger = get_logger(__name__)


class UserService:
    def __init__(self, user_repo: UserRepository) -> None:
        self._user_repo = user_repo

    async def get_user(self, user_id: uuid.UUID) -> UserResponse:
        user = await self._user_repo.get_with_roles(user_id)
        if not user:
            raise NotFoundError(detail="User not found")
        return self._to_response(user)

    async def list_users(self) -> list[UserResponse]:
        users = await self._user_repo.find()
        return [self._to_response(u) for u in users]

    async def update_user(self, user_id: uuid.UUID, **kwargs) -> UserResponse:
        user = await self._user_repo.update(user_id, **kwargs)
        if not user:
            raise NotFoundError(detail="User not found")
        user = await self._user_repo.get_with_roles(user_id)
        return self._to_response(user)

    async def delete_user(self, user_id: uuid.UUID) -> None:
        deleted = await self._user_repo.delete(user_id)
        if not deleted:
            raise NotFoundError(detail="User not found")

    async def assign_role(self, user_id: uuid.UUID, role_name: str) -> UserResponse:
        user = await self._user_repo.get(user_id)
        if not user:
            raise NotFoundError(detail="User not found")
        role = await self._user_repo.find_role_by_name(role_name)
        if not role:
            raise NotFoundError(detail=f"Role '{role_name}' not found")
        await self._user_repo.assign_role(user_id, role.id)
        user = await self._user_repo.get_with_roles(user_id)
        return self._to_response(user)

    async def remove_role(self, user_id: uuid.UUID, role_name: str) -> UserResponse:
        user = await self._user_repo.get(user_id)
        if not user:
            raise NotFoundError(detail="User not found")
        role = await self._user_repo.find_role_by_name(role_name)
        if not role:
            raise NotFoundError(detail=f"Role '{role_name}' not found")
        await self._user_repo.remove_role(user_id, role.id)
        user = await self._user_repo.get_with_roles(user_id)
        return self._to_response(user)

    @staticmethod
    def _to_response(user) -> UserResponse:
        return UserResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            is_verified=user.is_verified,
            roles=[ur.role.name for ur in user.roles],
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
