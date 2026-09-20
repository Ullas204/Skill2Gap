"""Ollama local provider using OpenAI-compatible API."""

from __future__ import annotations

import json
import time
from typing import AsyncIterator

import httpx

from app.ai_core.llm_client import LLMMessage, LLMResponse, LLMToolCall
from app.ai_core.providers.base import LLMProvider, ProviderConfig
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama local LLM via OpenAI-compatible endpoint."""

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None
        self._base_url = (config.base_url or "http://localhost:11434").rstrip("/")

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(self.config.timeout_seconds, connect=5.0),
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
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
            if tools:
                payload["tools"] = tools

            resp = await client.post("/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()

            elapsed = int((time.monotonic() - start) * 1000)
            message = data.get("message", {})
            content = message.get("content", "") or ""
            raw_tool_calls = message.get("tool_calls", [])

            tool_calls = []
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                tool_calls.append(LLMToolCall(
                    id=f"call_{func.get('name', 'unknown')}_{int(time.time() * 1000)}",
                    name=func.get("name", ""),
                    arguments=args,
                ))

            tokens = data.get("eval_count", 0) + data.get("prompt_eval_count", 0)
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
            logger.error("Ollama provider failed: %s", exc)
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
            "stream": True,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if tools:
            payload["tools"] = tools
        try:
            async with client.stream("POST", "/api/chat", json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        delta = chunk.get("message", {})
                        if "content" in delta and delta["content"]:
                            yield delta["content"]
                        if chunk.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.error("Ollama streaming failed: %s", exc)
            raise

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
