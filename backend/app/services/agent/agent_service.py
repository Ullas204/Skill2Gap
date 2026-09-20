"""Agent service layer - thin wrapper around ChatService for backward compat."""

from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.agent.chat_service import ChatService


class AgentService:
    def __init__(self, db: AsyncSession) -> None:
        self._chat = ChatService(db)

    async def chat(
        self,
        user_id: str,
        user_roles: list[str],
        message: str,
        conversation_id: str | None = None,
        user_name: str = "",
        user_email: str = "",
    ) -> dict:
        return await self._chat.chat(
            user_id=user_id,
            user_roles=user_roles,
            message=message,
            conversation_id=conversation_id,
            user_name=user_name,
            user_email=user_email,
        )

    async def get_conversations(self, user_id: str, limit: int = 20) -> list[dict]:
        convs = await self._chat._conv_repo.get_user_conversations(uuid.UUID(user_id), limit)
        return [
            {
                "id": str(c.id),
                "title": c.title,
                "agent_type": c.agent_type,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None,
            }
            for c in convs
        ]

    async def get_conversation_messages(self, conversation_id: str, user_id: str) -> dict:
        conv = await self._chat._conv_repo.get_with_messages(uuid.UUID(conversation_id))
        if not conv or str(conv.user_id) != user_id:
            return {"error": "Conversation not found"}
        messages = await self._chat._msg_repo.get_conversation_messages(conv.id)
        return {
            "id": str(conv.id),
            "title": conv.title,
            "agent_type": conv.agent_type,
            "messages": [
                {
                    "role": m.role,
                    "content": m.content,
                    "agent_type": m.agent_type,
                    "citations": m.citations,
                    "timestamp": m.created_at.isoformat() if m.created_at else None,
                }
                for m in messages
            ],
        }

    async def get_activity_logs(self, user_id: str, limit: int = 50) -> list[dict]:
        logs = await self._chat._log_repo.get_user_logs(uuid.UUID(user_id), limit)
        return [
            {
                "id": str(l.id),
                "agent_type": l.agent_type,
                "action": l.action,
                "details": l.details,
                "tokens_used": l.tokens_used,
                "latency_ms": l.latency_ms,
                "success": l.success,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]

    async def get_stats(self, user_id: str | None = None) -> dict:
        uid = uuid.UUID(user_id) if user_id else None
        return await self._chat._log_repo.get_stats(uid)

    def list_agents(self) -> list[dict]:
        return self._chat.list_agents()

    def list_tools(self) -> list[str]:
        return self._chat.list_tools()
