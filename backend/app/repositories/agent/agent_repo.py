"""Agent repository for database operations."""

from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.agent_models import (
    AgentConversation, AgentMessage, AgentToolExecution,
    AgentWorkflow, AgentActivityLog,
)
from app.repositories.base import BaseRepository


class AgentConversationRepository(BaseRepository[AgentConversation]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentConversation)

    async def get_user_conversations(self, user_id: uuid.UUID, limit: int = 20) -> list[AgentConversation]:
        stmt = (
            select(AgentConversation)
            .where(AgentConversation.user_id == user_id)
            .order_by(AgentConversation.updated_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_with_messages(self, conv_id: uuid.UUID) -> AgentConversation | None:
        stmt = select(AgentConversation).where(AgentConversation.id == conv_id)
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none()


class AgentMessageRepository(BaseRepository[AgentMessage]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentMessage)

    async def get_conversation_messages(self, conv_id: uuid.UUID, limit: int = 50) -> list[AgentMessage]:
        stmt = (
            select(AgentMessage)
            .where(AgentMessage.conversation_id == conv_id)
            .order_by(AgentMessage.created_at)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class AgentToolExecutionRepository(BaseRepository[AgentToolExecution]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentToolExecution)


class AgentWorkflowRepository(BaseRepository[AgentWorkflow]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentWorkflow)

    async def get_user_workflows(self, user_id: uuid.UUID, limit: int = 20) -> list[AgentWorkflow]:
        stmt = (
            select(AgentWorkflow)
            .where(AgentWorkflow.user_id == user_id)
            .order_by(AgentWorkflow.updated_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())


class AgentActivityLogRepository(BaseRepository[AgentActivityLog]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, AgentActivityLog)

    async def get_user_logs(self, user_id: uuid.UUID, limit: int = 50) -> list[AgentActivityLog]:
        stmt = (
            select(AgentActivityLog)
            .where(AgentActivityLog.user_id == user_id)
            .order_by(AgentActivityLog.created_at.desc())
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def get_stats(self, user_id: uuid.UUID | None = None) -> dict:
        stmt = select(
            func.count(AgentActivityLog.id),
            func.coalesce(func.sum(AgentActivityLog.tokens_used), 0),
            func.coalesce(func.avg(AgentActivityLog.latency_ms), 0),
        )
        if user_id:
            stmt = stmt.where(AgentActivityLog.user_id == user_id)
        result = await self._session.execute(stmt)
        row = result.one()
        return {
            "total_actions": row[0],
            "total_tokens": int(row[1]),
            "avg_latency_ms": float(row[2]),
        }
