"""Tool registry for the Agentic AI platform.

Tools are callable functions that agents can invoke to interact with
the platform's backend services.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ToolMeta:
    name: str
    description: str
    parameters: dict
    handler: Callable[..., Awaitable[Any]]
    required_roles: list[str] = field(default_factory=list)
    required_permissions: list[str] = field(default_factory=list)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolMeta] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable[..., Awaitable[Any]],
        required_roles: list[str] | None = None,
        required_permissions: list[str] | None = None,
    ) -> None:
        self._tools[name] = ToolMeta(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
            required_roles=required_roles or [],
            required_permissions=required_permissions or [],
        )

    def get_handler(self, name: str) -> Callable[..., Awaitable[Any]] | None:
        tool = self._tools.get(name)
        return tool.handler if tool else None

    def get_tool(self, name: str) -> ToolMeta | None:
        return self._tools.get(name)

    def get_definitions_for_role(self, role: str) -> list[dict]:
        defs = []
        for tool in self._tools.values():
            if not tool.required_roles or role in tool.required_roles or "admin" in role:
                defs.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters,
                    },
                })
        return defs

    def list_tools(self) -> list[str]:
        return list(self._tools.keys())

    async def execute(self, name: str, user_roles: list[str], **kwargs) -> dict:
        tool = self._tools.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}

        if tool.required_roles:
            has_role = any(r in tool.required_roles for r in user_roles) or "admin" in user_roles
            if not has_role:
                return {"error": f"Insufficient permissions to use tool: {name}"}

        start = time.monotonic()
        try:
            result = await tool.handler(**kwargs)
            elapsed = int((time.monotonic() - start) * 1000)
            return {
                "success": True,
                "result": result if isinstance(result, dict) else {"output": str(result)},
                "execution_time_ms": elapsed,
                "tool_id": str(uuid.uuid4()),
            }
        except Exception as exc:
            elapsed = int((time.monotonic() - start) * 1000)
            logger.error("Tool execution failed: %s -> %s", name, exc)
            return {
                "success": False,
                "error": str(exc),
                "execution_time_ms": elapsed,
                "tool_id": str(uuid.uuid4()),
            }


tool_registry = ToolRegistry()
