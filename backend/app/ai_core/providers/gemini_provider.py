"""Google Gemini provider using the REST API."""

from __future__ import annotations

import json
import time
from typing import AsyncIterator

import httpx

from app.ai_core.llm_client import LLMMessage, LLMResponse, LLMToolCall
from app.ai_core.providers.base import LLMProvider, ProviderConfig
from app.core.logging import get_logger

logger = get_logger(__name__)


class GeminiProvider(LLMProvider):
    """Google Gemini via REST API (generativelanguage.googleapis.com)."""

    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, config: ProviderConfig) -> None:
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout_seconds, connect=10.0),
            )
        return self._client

    def _to_gemini_contents(self, messages: list[LLMMessage]) -> tuple[dict | None, list[dict]]:
        system_instruction = None
        contents = []
        for m in messages:
            if m.role == "system":
                system_instruction = {"parts": [{"text": m.content}]}
            elif m.role == "user":
                contents.append({"role": "user", "parts": [{"text": m.content}]})
            elif m.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": m.content or ""}]})
            elif m.role == "tool":
                contents.append({"role": "user", "parts": [{"text": m.content}]})
        if not contents:
            contents.append({"role": "user", "parts": [{"text": ""}]})
        return system_instruction, contents

    def _to_gemini_tools(self, tools: list[dict] | None) -> dict | None:
        if not tools:
            return None
        declarations = []
        for t in tools:
            func = t.get("function", {})
            declarations.append({
                "name": func.get("name", ""),
                "description": func.get("description", ""),
                "parameters": func.get("parameters", {}),
            })
        return {"function_declarations": declarations}

    def _parse_gemini_response(self, data: dict) -> tuple[str, list[LLMToolCall]]:
        candidates = data.get("candidates", [])
        if not candidates:
            return "", []
        candidate = candidates[0]
        content = candidate.get("content", {})
        parts = content.get("parts", [])
        text_parts = []
        tool_calls = []
        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])
            elif "functionCall" in part:
                fc = part["functionCall"]
                args = fc.get("args", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except (json.JSONDecodeError, TypeError):
                        args = {}
                tool_calls.append(LLMToolCall(
                    id=f"call_{fc.get('name', 'unknown')}_{int(time.time() * 1000)}",
                    name=fc.get("name", ""),
                    arguments=args,
                ))
        return "\n".join(text_parts), tool_calls

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
            system_instruction, contents = self._to_gemini_contents(messages)
            model = self.config.model or "gemini-2.5-flash"

            payload: dict = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                    "maxOutputTokens": max_tokens,
                },
            }
            if system_instruction:
                payload["systemInstruction"] = system_instruction

            gemini_tools = self._to_gemini_tools(tools)
            if gemini_tools:
                payload["tools"] = [gemini_tools]

            url = f"{self.BASE_URL}/models/{model}:generateContent?key={self.config.api_key}"
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                raise ValueError(data["error"].get("message", "Gemini API error"))

            content, tool_calls = self._parse_gemini_response(data)
            elapsed = int((time.monotonic() - start) * 1000)
            self.health.record_success(elapsed)

            usage = data.get("usageMetadata", {})
            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                tokens_used=usage.get("totalTokenCount", 0),
                latency_ms=elapsed,
                model=model,
            )
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            self.health.record_failure(str(exc))
            logger.error("Gemini provider failed: %s", exc)
            raise

    async def stream_chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        client = await self._get_client()
        system_instruction, contents = self._to_gemini_contents(messages)
        model = self.config.model or "gemini-2.5-flash"

        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
            },
        }
        if system_instruction:
            payload["systemInstruction"] = system_instruction
        gemini_tools = self._to_gemini_tools(tools)
        if gemini_tools:
            payload["tools"] = [gemini_tools]

        url = f"{self.BASE_URL}/models/{model}:streamGenerateContent?key={self.config.api_key}&alt=sse"
        try:
            async with client.stream("POST", url, json=payload) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    chunk_str = line[6:]
                    if chunk_str.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(chunk_str)
                        candidates = chunk.get("candidates", [])
                        if candidates:
                            parts = candidates[0].get("content", {}).get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    yield part["text"]
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.error("Gemini streaming failed: %s", exc)
            raise

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
