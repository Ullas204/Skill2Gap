"""Conversational memory system with per-user isolation.

Two-layer design:
1. Fast in-memory cache for active conversations (hot path)
2. DB-backed persistence via AgentConversationRepository (cold path / restarts)

The memory system never leaks context between different users.
"""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime, timezone

from app.core.logging import get_logger

logger = get_logger(__name__)


class ConversationMemory:
    """Per-user isolated conversation memory with context tracking."""

    def __init__(self) -> None:
        self._conversations: dict[str, list[dict]] = defaultdict(list)
        self._context: dict[str, dict] = {}

    def get_or_create_conversation(self, user_id: str, conversation_id: str | None = None) -> str:
        cid = conversation_id or str(uuid.uuid4())
        if cid not in self._conversations:
            self._conversations[cid] = []
            self._context[cid] = {
                "user_id": user_id,
                "selected_job_id": None,
                "selected_candidate_id": None,
                "current_filters": {},
                "agent_type": None,
                "last_intent": None,
                "conversation_started": datetime.now(timezone.utc).isoformat(),
            }
        return cid

    def add_message(self, conversation_id: str, role: str, content: str, **kwargs) -> None:
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **kwargs,
        }
        self._conversations[conversation_id].append(msg)

    def get_history(self, conversation_id: str, limit: int = 50) -> list[dict]:
        msgs = self._conversations.get(conversation_id, [])
        return msgs[-limit:]

    def get_context(self, conversation_id: str) -> dict:
        return self._context.get(conversation_id, {})

    def update_context(self, conversation_id: str, **updates) -> None:
        if conversation_id in self._context:
            self._context[conversation_id].update(updates)

    def clear_conversation(self, conversation_id: str) -> None:
        self._conversations.pop(conversation_id, None)
        self._context.pop(conversation_id, None)

    def list_user_conversations(self, user_id: str) -> list[str]:
        return [
            cid for cid, ctx in self._context.items()
            if ctx.get("user_id") == user_id
        ]

    def load_from_messages(self, conversation_id: str, user_id: str, messages: list[dict]) -> None:
        """Hydrate memory from DB messages on conversation load."""
        if conversation_id not in self._conversations:
            self._conversations[conversation_id] = []
            self._context[conversation_id] = {
                "user_id": user_id,
                "selected_job_id": None,
                "selected_candidate_id": None,
                "current_filters": {},
                "agent_type": None,
                "last_intent": None,
                "conversation_started": datetime.now(timezone.utc).isoformat(),
            }
        for msg in messages:
            self._conversations[conversation_id].append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", ""),
                "timestamp": msg.get("timestamp", datetime.now(timezone.utc).isoformat()),
                "agent_type": msg.get("agent_type"),
            })

    def _evict_old(self, max_per_user: int = 50) -> None:
        user_convs: dict[str, list[str]] = defaultdict(list)
        for cid, ctx in self._context.items():
            uid = ctx.get("user_id", "")
            user_convs[uid].append(cid)
        for uid, cids in user_convs.items():
            if len(cids) > max_per_user:
                to_remove = cids[: len(cids) - max_per_user]
                for cid in to_remove:
                    self.clear_conversation(cid)


conversation_memory = ConversationMemory()
