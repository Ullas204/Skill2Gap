import uuid
from typing import Any, Generic, TypeVar

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    def __init__(self, session: AsyncSession, model: type[ModelT]) -> None:
        self._session = session
        self._model = model

    async def create(self, **kwargs: Any) -> ModelT:
        instance = self._model(**kwargs)
        self._session.add(instance)
        await self._session.flush()
        return instance

    async def get(self, id: uuid.UUID | int) -> ModelT | None:
        stmt = select(self._model).where(self._model.id == id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def find(self, **filters: Any) -> list[ModelT]:
        stmt = select(self._model).filter_by(**filters)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def find_one(self, **filters: Any) -> ModelT | None:
        stmt = select(self._model).filter_by(**filters)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, id: uuid.UUID | int, **kwargs: Any) -> ModelT | None:
        stmt = update(self._model).where(self._model.id == id).values(**kwargs)
        await self._session.execute(stmt)
        await self._session.flush()
        return await self.get(id)

    async def delete(self, id: uuid.UUID | int) -> bool:
        stmt = delete(self._model).where(self._model.id == id)
        result = await self._session.execute(stmt)
        await self._session.flush()
        return result.rowcount > 0

    async def exists(self, **filters: Any) -> bool:
        stmt = select(self._model).filter_by(**filters).limit(1)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None
