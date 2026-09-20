"""SQLAlchemy models for the Agentic AI platform."""

from __future__ import annotations

import uuid

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, JSON, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDMixin


class AgentConversation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_conversations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    agent_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)

    user: Mapped["User"] = relationship("User", backref="agent_conversations")
    messages: Mapped[list["AgentMessage"]] = relationship(
        "AgentMessage", back_populates="conversation", cascade="all, delete-orphan",
        order_by="AgentMessage.created_at",
    )


class AgentMessage(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_messages"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tool_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tool_call_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    citations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    conversation: Mapped["AgentConversation"] = relationship(
        "AgentConversation", back_populates="messages",
    )


class AgentToolExecution(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_tool_executions"

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("agent_conversations.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    message_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_messages.id", ondelete="SET NULL"), nullable=True,
    )
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    arguments: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    conversation: Mapped["AgentConversation"] = relationship("AgentConversation", backref="tool_executions")


class AgentWorkflow(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_workflows"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True,
    )
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("agent_conversations.id", ondelete="SET NULL"), nullable=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    steps: Mapped[list | None] = mapped_column(JSON, nullable=True)
    current_step: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    trigger_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship("User", backref="agent_workflows")


class AgentActivityLog(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_activity_logs"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True,
    )
    agent_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    user: Mapped["User | None"] = relationship("User", backref="agent_activity_logs")


class KnowledgeDocument(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "knowledge_documents"

    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    embedding_id: Mapped[str | None] = mapped_column(String(200), nullable=True, unique=True)
    is_indexed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
