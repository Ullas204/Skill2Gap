"""Base LLM provider abstraction.

All providers implement the same interface so the router can switch
between them seamlessly. Each provider handles its own API format
normalization into the common LLMMessage/LLMResponse types.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import AsyncIterator

from app.ai_core.llm_client import LLMMessage, LLMResponse, LLMToolCall


class ProviderStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ProviderConfig:
    name: str
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    timeout_seconds: int = 60
    max_retries: int = 2
    priority: int = 0


@dataclass
class ProviderHealth:
    provider: str
    status: ProviderStatus = ProviderStatus.UNKNOWN
    last_check: float = 0.0
    last_error: str = ""
    consecutive_failures: int = 0
    total_requests: int = 0
    total_failures: int = 0
    avg_latency_ms: float = 0.0
    _latency_sum: float = 0.0

    def record_success(self, latency_ms: float) -> None:
        self.consecutive_failures = 0
        self.total_requests += 1
        self.status = ProviderStatus.HEALTHY
        self._latency_sum += latency_ms
        self.avg_latency_ms = self._latency_sum / self.total_requests
        self.last_check = time.time()

    def record_failure(self, error: str) -> None:
        self.consecutive_failures += 1
        self.total_failures += 1
        self.total_requests += 1
        self.last_error = error
        self.last_check = time.time()
        if self.consecutive_failures >= 3:
            self.status = ProviderStatus.UNHEALTHY
        else:
            self.status = ProviderStatus.DEGRADED

    @property
    def is_available(self) -> bool:
        return self.status != ProviderStatus.UNHEALTHY

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 1.0
        return 1.0 - (self.total_failures / self.total_requests)


class LLMProvider(ABC):
    """Abstract base for all LLM providers."""

    def __init__(self, config: ProviderConfig) -> None:
        self.config = config
        self.health = ProviderHealth(provider=config.name)

    @property
    def name(self) -> str:
        return self.config.name

    @abstractmethod
    async def chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def stream_chat(
        self,
        messages: list[LLMMessage],
        tools: list[dict] | None = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncIterator[str]:
        ...

    async def health_check(self) -> ProviderHealth:
        return self.health

    @abstractmethod
    async def close(self) -> None:
        ...
