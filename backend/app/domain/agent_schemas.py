"""Pydantic schemas for the Agentic AI platform."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────


class AgentType(str, Enum):
    CANDIDATE = "candidate"
    RECRUITER = "recruiter"
    HR = "hr"
    ADMIN = "admin"
    RESUME = "resume"
    JOB_MATCHING = "job_matching"
    INTERVIEW = "interview"
    ANALYTICS = "analytics"
    FAIRNESS = "fairness"
    REPORT = "report"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


class ToolCallStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowStepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    AWAITING_CONFIRMATION = "awaiting_confirmation"


# ── Tool Calling ──────────────────────────────────────────────────


class ToolCallInfo(BaseModel):
    id: str
    name: str
    arguments: dict
    status: ToolCallStatus = ToolCallStatus.PENDING


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict
    required_roles: list[str] = []
    required_permissions: list[str] = []


class ToolExecutionResponse(BaseModel):
    id: str
    tool_name: str
    arguments: dict
    result: dict | None = None
    status: ToolCallStatus
    error: str | None = None
    execution_time_ms: int = 0


# ── RAG ───────────────────────────────────────────────────────────


class Citation(BaseModel):
    source_type: str
    source_id: str
    title: str
    excerpt: str
    relevance_score: float = 0.0


class RAGQuery(BaseModel):
    query: str
    source_types: list[str] | None = None
    top_k: int = 5


class RAGResult(BaseModel):
    content: str
    source_type: str
    source_id: str
    metadata: dict = {}
    score: float = 0.0


# ── Chat Request / Response ───────────────────────────────────────


class ChatMessage(BaseModel):
    role: MessageRole
    content: str
    tool_calls: list[ToolCallInfo] | None = None
    tool_call_id: str | None = None
    citations: list[Citation] | None = None
    agent_type: AgentType | None = None
    timestamp: datetime | None = None


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=10000)
    conversation_id: uuid.UUID | None = None
    stream: bool = False


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message: ChatMessage
    tool_executions: list[ToolExecutionResponse] = []
    agent_used: AgentType
    processing_time_ms: int = 0
    provider_used: str = ""
    tokens_used: int = 0


class ChatStreamEvent(BaseModel):
    event: str  # "metadata", "start", "delta", "done", "error", "tool_call", "tool_result"
    data: dict


# ── Provider Info ─────────────────────────────────────────────────


class ProviderInfo(BaseModel):
    name: str
    model: str
    status: str
    success_rate: float
    avg_latency_ms: float
    total_requests: int


# ── Conversation / Memory ─────────────────────────────────────────


class ConversationResponse(BaseModel):
    id: uuid.UUID
    title: str | None = None
    agent_type: AgentType | None = None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = {"from_attributes": True}


class ConversationDetailResponse(BaseModel):
    id: uuid.UUID
    title: str | None = None
    agent_type: AgentType | None = None
    messages: list[ChatMessage] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Workflow ──────────────────────────────────────────────────────


class WorkflowStepRequest(BaseModel):
    name: str
    tool_name: str
    arguments: dict = {}
    confirmation_required: bool = False


class WorkflowDefinitionRequest(BaseModel):
    name: str
    description: str
    steps: list[WorkflowStepRequest]
    trigger_message: str | None = None


class WorkflowStepResponse(BaseModel):
    name: str
    tool_name: str
    status: WorkflowStepStatus
    result: dict | None = None
    error: str | None = None


class WorkflowResponse(BaseModel):
    id: uuid.UUID
    name: str
    status: WorkflowStatus
    steps: list[WorkflowStepResponse] = []
    current_step: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ── Reports ───────────────────────────────────────────────────────


class ReportGenerateRequest(BaseModel):
    report_type: str
    title: str | None = None
    parameters: dict = {}
    export_format: str = "pdf"


class ReportResponse(BaseModel):
    id: uuid.UUID
    title: str
    report_type: str
    content: dict | None = None
    export_url: str | None = None
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Agent Activity / Observability ────────────────────────────────


class AgentActivityResponse(BaseModel):
    id: uuid.UUID
    agent_type: AgentType
    action: str
    details: dict | None = None
    tokens_used: int = 0
    latency_ms: int = 0
    success: bool = True
    created_at: datetime

    model_config = {"from_attributes": True}


class AgentStatsResponse(BaseModel):
    total_conversations: int = 0
    total_messages: int = 0
    total_tool_calls: int = 0
    total_workflows: int = 0
    total_tokens_used: int = 0
    avg_response_time_ms: float = 0.0
    agent_usage: dict = {}
    top_tools: list[dict] = []
