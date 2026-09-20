"""Groq provider using OpenAI-compatible API."""

from __future__ import annotations

import json
import time
from typing import AsyncIterator

import httpx

from app.ai_core.llm_client import LLMMessage, LLMResponse, LLMToolCall
from app.ai_core.providers.base import LLMProvider, ProviderConfig
from app.core.logging import get_logger

logger = get_logger(__name__)


class GroqProvider(LLMProvider):
    """Groq via OpenAI-compatible API (api.groq.com/openai)."""

    BASE_URL = "https://api.groq.com/openai/v1"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(self.config.timeout_seconds, connect=10.0),
            )
        return self._client

    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        start = time.monotonic()
        try:
            client = await self._get_client()
            payload: dict = {
                "model": self.config.model,
                "messages": [{"role": m.role, "content": m.content} for m in messages],
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            resp = await client.post("/chat/completions", json=payload)
            resp.raise_for_status()
            data = resp.json()

            elapsed = int((time.monotonic() - start) * 1000)
            choice = data.get("choices", [{}])[0]
            msg = choice.get("message", {})
            content = msg.get("content", "") or ""
            raw_tool_calls = msg.get("tool_calls", [])
            tokens = data.get("usage", {}).get("total_tokens", 0)

            tool_calls = [
                LLMToolCall(
                    id=tc["id"],
                    name=tc["function"]["name"],
                    arguments=json.loads(tc["function"]["arguments"]) if isinstance(tc["function"]["arguments"], str) else tc["function"]["arguments"],
                )
                for tc in raw_tool_calls
            ]

            self.health.record_success(elapsed)
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                tokens_used=tokens,
                latency_ms=elapsed,
                model=self.config.model,
            )
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            self.health.record_failure(str(exc))
            logger.error("Groq provider failed: %s", exc)
            raise

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        client = await self._get_client()
        payload: dict = {
            "model": self.config.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
        try:
            async with client.stream("POST", "/chat/completions", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    chunk_str = line[6:]
                    if chunk_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(chunk_str)
                        delta = chunk.get("choices", [{}])[0].get("delta", {})
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.error("Groq streaming failed: %s", exc)
            raise

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
