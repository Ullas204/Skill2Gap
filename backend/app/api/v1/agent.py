"""Agent API — RBAC-protected endpoints for the Agentic AI platform."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.domain.agent_schemas import (
    ChatRequest, ChatResponse, ConversationResponse, ConversationDetailResponse,
    AgentActivityResponse, AgentStatsResponse, WorkflowDefinitionRequest,
    WorkflowResponse, ReportGenerateRequest, ReportResponse, ChatMessage, MessageRole,
    ProviderInfo,
)
from app.domain.models import User
from app.services.agent.chat_service import ChatService

router = APIRouter(prefix="/agent", tags=["agent"])


def _get_service(db: AsyncSession = Depends(get_db)) -> ChatService:
    return ChatService(db)


# ─── Chat ─────────────────────────────────────────────────────────


@router.post("/chat")
async def chat(
    body: ChatRequest,
    current_user: User = Depends(require_role("candidate", "recruiter", "hr", "admin")),
    service: ChatService = Depends(_get_service),
):
    user_roles = [ur.role.name for ur in current_user.roles]

    if body.stream:
        return StreamingResponse(
            service.stream_chat(
                user_id=str(current_user.id),
                user_roles=user_roles,
                message=body.message,
                conversation_id=str(body.conversation_id) if body.conversation_id else None,
                user_name=current_user.full_name,
                user_email=current_user.email,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    result = await service.chat(
        user_id=str(current_user.id),
        user_roles=user_roles,
        message=body.message,
        conversation_id=str(body.conversation_id) if body.conversation_id else None,
        user_name=current_user.full_name,
        user_email=current_user.email,
    )
    return result


# ─── Conversations ────────────────────────────────────────────────


@router.get("/conversations")
async def list_conversations(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_service),
):
    convs = await _list_convos(service, str(current_user.id))
    return {"conversations": convs}


async def _list_convos(service: ChatService, user_id: str, limit: int = 20) -> list[dict]:
    from app.repositories.agent.agent_repo import AgentConversationRepository
    from uuid import UUID
    convs = await service._conv_repo.get_user_conversations(UUID(user_id), limit)
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


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: str,
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_service),
):
    from uuid import UUID
    conv = await service._conv_repo.get_with_messages(UUID(conversation_id))
    if not conv or str(conv.user_id) != str(current_user.id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    messages = await service._msg_repo.get_conversation_messages(conv.id)
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


# ─── Activity & Stats ─────────────────────────────────────────────


@router.get("/activity")
async def get_activity_logs(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_service),
):
    from uuid import UUID
    logs = await service._log_repo.get_user_logs(UUID(str(current_user.id)), 50)
    return {
        "activity": [
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
    }


@router.get("/stats")
async def get_stats(
    current_user: User = Depends(require_role("admin", "hr")),
    service: ChatService = Depends(_get_service),
):
    from uuid import UUID
    return await service._log_repo.get_stats(UUID(str(current_user.id)))


# ─── Agent Info ───────────────────────────────────────────────────


@router.get("/agents")
async def list_agents(
    current_user: User = Depends(get_current_user),
    service: ChatService = Depends(_get_service),
):
    return {"agents": service.list_agents()}


@router.get("/tools")
async def list_tools(
    current_user: User = Depends(require_role("recruiter", "hr", "admin")),
    service: ChatService = Depends(_get_service),
):
    return {"tools": service.list_tools()}


@router.get("/providers")
async def list_providers(
    current_user: User = Depends(require_role("admin", "hr")),
    service: ChatService = Depends(_get_service),
):
    return {"providers": service.get_providers()}


# ─── Workflows ────────────────────────────────────────────────────


@router.get("/workflows")
async def list_workflows(
    current_user: User = Depends(get_current_user),
):
    from app.ai_core.workflow_engine import workflow_engine
    templates = workflow_engine.get_predefined_workflows()
    return {"workflows": templates}


@router.post("/workflows")
async def create_workflow(
    body: WorkflowDefinitionRequest,
    current_user: User = Depends(require_role("recruiter", "hr", "admin")),
):
    from app.ai_core.workflow_engine import workflow_engine
    steps = [{"name": s.name, "tool_name": s.tool_name, "arguments": s.arguments, "confirmation_required": s.confirmation_required} for s in body.steps]
    wf = workflow_engine.create_workflow(body.name, steps, str(current_user.id))
    return {"workflow_id": wf.id, "name": wf.name, "status": wf.status, "steps_count": len(wf.steps)}


@router.post("/workflows/{workflow_id}/execute")
async def execute_workflow_step(
    workflow_id: str,
    current_user: User = Depends(require_role("recruiter", "hr", "admin")),
):
    from app.ai_core.workflow_engine import workflow_engine
    return await workflow_engine.execute_next_step(workflow_id)


@router.post("/workflows/{workflow_id}/confirm")
async def confirm_workflow_step(
    workflow_id: str,
    current_user: User = Depends(require_role("recruiter", "hr", "admin")),
):
    from app.ai_core.workflow_engine import workflow_engine
    return await workflow_engine.confirm_step(workflow_id)


@router.post("/workflows/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: str,
    current_user: User = Depends(require_role("recruiter", "hr", "admin")),
):
    from app.ai_core.workflow_engine import workflow_engine
    return await workflow_engine.cancel_workflow(workflow_id)


# ─── Reports ──────────────────────────────────────────────────────


@router.post("/reports/generate")
async def generate_report(
    body: ReportGenerateRequest,
    current_user: User = Depends(require_role("recruiter", "hr", "admin")),
):
    from app.tools.executor import tool_executor
    result = await tool_executor.execute(
        "generate_report",
        [ur.role.name for ur in current_user.roles],
        report_type=body.report_type,
        title=body.title or "",
    )
    return result.get("result", result)


@router.post("/reports/export")
async def export_report(
    body: ReportGenerateRequest,
    current_user: User = Depends(require_role("recruiter", "hr", "admin")),
):
    from app.tools.executor import tool_executor
    result = await tool_executor.execute(
        "export_report",
        [ur.role.name for ur in current_user.roles],
        report_type=body.report_type,
        format=body.export_format,
    )
    return result.get("result", result)
