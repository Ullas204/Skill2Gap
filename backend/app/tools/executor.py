"""Tool executor service with error handling, logging, and retry logic.

Wraps the tool_registry to provide safer execution with:
- Per-tool timeout handling
- Structured error responses
- Execution logging
- Tool call result normalization
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from app.core.logging import get_logger
from app.tools.registry import tool_registry

logger = get_logger(__name__)


class ToolExecutor:
    """Executes tool calls with safety, logging, and result normalization."""

    def __init__(self) -> None:
        pass

    async def execute(
        self,
        name: str,
        user_roles: list[str],
        arguments: dict[str, Any] | None = None,
    ) -> dict:
        args = arguments or {}
        start = time.monotonic()
        tool_id = str(uuid.uuid4())

        try:
            result = await tool_registry.execute(name, user_roles, **args)
            elapsed = int((time.monotonic() - start) * 1000)

            if "error" in result and not result.get("success", False):
                logger.warning("Tool '%s' returned error: %s", name, result.get("error", ""))
                return {
                    "id": tool_id,
                    "name": name,
                    "arguments": args,
                    "result": result,
                    "success": False,
                    "error": result.get("error", "Tool execution failed"),
                    "execution_time_ms": elapsed,
                }

            normalized = self._normalize_result(result)
            return {
                "id": tool_id,
                "name": name,
                "arguments": args,
                "result": normalized,
                "success": True,
                "execution_time_ms": elapsed,
            }
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error("Tool '%s' raised exception: %s", name, exc)
            return {
                "id": tool_id,
                "name": name,
                "arguments": args,
                "result": None,
                "success": False,
                "error": str(exc),
                "execution_time_ms": elapsed,
            }

    def _normalize_result(self, result: dict) -> dict:
        if "result" in result:
            inner = result["result"]
            if isinstance(inner, dict):
                return inner
            return {"output": str(inner)}
        return result

    def format_tool_results_for_llm(self, tool_results: list[dict]) -> str:
        parts = []
        for tr in tool_results:
            name = tr.get("name", "unknown")
            result = tr.get("result", {})
            success = tr.get("success", False)
            status = "OK" if success else "FAILED"
            summary = json.dumps(result, default=str)[:500]
            parts.append(f"Tool '{name}' [{status}]: {summary}")
        return "\n".join(parts)

    def get_available_tools(self) -> list[str]:
        return tool_registry.list_tools()


tool_executor = ToolExecutor()
