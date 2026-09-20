import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domain.models import Role, User, UserRole
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_with_roles(self, id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRole.role))
            .where(User.id == id)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_with_roles(self, email: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.roles).selectinload(UserRole.role))
            .where(User.email == email)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def assign_role(self, user_id: uuid.UUID, role_id: int) -> UserRole:
        user_role = UserRole(user_id=user_id, role_id=role_id)
        self._session.add(user_role)
        await self._session.flush()
        return user_role

    async def remove_role(self, user_id: uuid.UUID, role_id: int) -> bool:
        result = await self._session.execute(
            select(UserRole).where(
                UserRole.user_id == user_id, UserRole.role_id == role_id,
            )
        )
        user_role = result.scalar_one_or_none()
        if user_role:
            await self._session.delete(user_role)
            await self._session.flush()
            return True
        return False

    async def get_user_roles(self, user_id: uuid.UUID) -> list[Role]:
        stmt = (
            select(Role)
            .join(UserRole)
            .where(UserRole.user_id == user_id)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_role_by_name(self, name: str) -> Role | None:
        stmt = select(Role).where(Role.name == name)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_roles(self) -> list[Role]:
        stmt = select(Role)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())
