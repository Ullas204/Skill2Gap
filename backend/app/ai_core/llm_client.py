"""LLM client abstraction for the Agentic AI platform.

Delegates to the multi-LLM Router for actual API calls. Retains the
same public interface (LLMMessage, LLMResponse, LLMToolCall) so all
existing agent code continues to work without modification.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMToolCall:
    id: str
    name: str
    arguments: dict


@dataclass
class LLMResponse:
    content: str
    tool_calls: list[LLMToolCall] = field(default_factory=list)
    tokens_used: int = 0
    latency_ms: int = 0
    model: str = ""


class LLMClient:
    """Async LLM client that delegates to the multi-provider router."""

    def __init__(self, **kwargs: Any) -> None:
        pass

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        from app.ai_core.llm_router import llm_router
        return await llm_router.chat(messages, tools, temperature, max_tokens)

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        from app.ai_core.llm_router import llm_router
        async for chunk in llm_router.stream_chat(messages, tools, temperature, max_tokens):
            yield chunk

    async def close(self) -> None:
        from app.ai_core.llm_router import llm_router
        await llm_router.close()


llm_client = LLMClient()
