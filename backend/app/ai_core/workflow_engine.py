"""Workflow engine for multi-step AI automation."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field

from app.core.logging import get_logger
from app.tools.registry import tool_registry

logger = get_logger(__name__)


@dataclass
class WorkflowStep:
    name: str
    tool_name: str
    arguments: dict = field(default_factory=dict)
    confirmation_required: bool = False
    status: str = "pending"
    result: dict | None = None
    error: str | None = None


@dataclass
class Workflow:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    current_step: int = 0
    status: str = "pending"
    user_id: str = ""
    conversation_id: str = ""


PREDEFINED_WORKFLOWS: dict[str, list[dict]] = {
    "full_hiring_pipeline": [
        {"name": "Create Job", "tool_name": "create_job", "confirmation_required": True},
        {"name": "Publish Job", "tool_name": "update_job_status", "confirmation_required": True},
        {"name": "Notify Candidates", "tool_name": "send_notification", "confirmation_required": True},
        {"name": "Screen Applicants", "tool_name": "screen_candidates"},
        {"name": "Rank Candidates", "tool_name": "rank_candidates"},
        {"name": "Generate Interview Kit", "tool_name": "generate_interview_questions"},
        {"name": "Schedule Interviews", "tool_name": "schedule_interview", "confirmation_required": True},
        {"name": "Generate Hiring Report", "tool_name": "generate_report"},
    ],
    "candidate_evaluation": [
        {"name": "Search Candidates", "tool_name": "search_candidates"},
        {"name": "Rank Candidates", "tool_name": "rank_candidates"},
        {"name": "Compare Top Candidates", "tool_name": "compare_candidates"},
        {"name": "Explain Scores", "tool_name": "explain_candidate_score"},
    ],
    "interview_preparation": [
        {"name": "Generate Questions", "tool_name": "generate_interview_questions"},
        {"name": "Analyze Fairness", "tool_name": "analyze_fairness"},
        {"name": "Generate Scorecard Template", "tool_name": "generate_report"},
    ],
    "compliance_audit": [
        {"name": "Analyze Fairness", "tool_name": "analyze_fairness"},
        {"name": "Run Adversarial Testing", "tool_name": "adversarial_fairness_test"},
        {"name": "Analyze Job Description Bias", "tool_name": "analyze_jd_bias"},
        {"name": "Generate Compliance Report", "tool_name": "generate_report"},
    ],
}


class WorkflowEngine:
    def __init__(self) -> None:
        self._workflows: dict[str, Workflow] = {}

    def get_predefined_workflows(self) -> list[dict]:
        return [
            {"name": name, "description": name.replace("_", " ").title(), "steps": [s["name"] for s in steps]}
            for name, steps in PREDEFINED_WORKFLOWS.items()
        ]

    def create_workflow(
        self,
        name: str,
        steps: list[dict],
        user_id: str,
        conversation_id: str = "",
    ) -> Workflow:
        wf_steps = [
            WorkflowStep(
                name=s.get("name", f"Step {i+1}"),
                tool_name=s.get("tool_name", ""),
                arguments=s.get("arguments", {}),
                confirmation_required=s.get("confirmation_required", False),
            )
            for i, s in enumerate(steps)
        ]
        wf = Workflow(
            name=name,
            description=f"Workflow: {name}",
            steps=wf_steps,
            user_id=user_id,
            conversation_id=conversation_id,
        )
        self._workflows[wf.id] = wf
        return wf

    def create_from_template(self, template_name: str, user_id: str, conversation_id: str = "") -> Workflow | None:
        template = PREDEFINED_WORKFLOWS.get(template_name)
        if not template:
            return None
        return self.create_workflow(template_name, template, user_id, conversation_id)

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        return self._workflows.get(workflow_id)

    async def execute_next_step(self, workflow_id: str, context: dict | None = None) -> dict:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return {"error": "Workflow not found"}

        if wf.current_step >= len(wf.steps):
            wf.status = "completed"
            return {"status": "completed", "message": "Workflow completed"}

        step = wf.steps[wf.current_step]

        if step.status == "awaiting_confirmation":
            return {
                "status": "awaiting_confirmation",
                "step": step.name,
                "message": f"Step '{step.name}' requires confirmation before execution.",
            }

        if step.confirmation_required and step.status == "pending":
            step.status = "awaiting_confirmation"
            wf.status = "paused"
            return {
                "status": "awaiting_confirmation",
                "step": step.name,
                "tool": step.tool_name,
                "arguments": step.arguments,
            }

        wf.status = "running"
        step.status = "running"
        start = time.monotonic()

        try:
            handler = tool_registry.get_handler(step.tool_name)
            if handler:
                merged_args = {**step.arguments, **(context or {})}
                result = await handler(**merged_args)
                step.result = result if isinstance(result, dict) else {"output": str(result)}
                step.status = "completed"
            else:
                step.result = {"output": f"Tool '{step.tool_name}' simulated successfully"}
                step.status = "completed"
        except Exception as exc:
            step.status = "failed"
            step.error = str(exc)
            wf.status = "failed"
            logger.error("Workflow step failed: %s -> %s", step.name, exc)
            return {"status": "failed", "step": step.name, "error": str(exc)}

        elapsed = int((time.monotonic() - start) * 1000)
        wf.current_step += 1

        if wf.current_step >= len(wf.steps):
            wf.status = "completed"

        return {
            "status": step.status,
            "step": step.name,
            "result": step.result,
            "execution_time_ms": elapsed,
            "workflow_status": wf.status,
        }

    async def confirm_step(self, workflow_id: str) -> dict:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return {"error": "Workflow not found"}
        step = wf.steps[wf.current_step]
        if step.status != "awaiting_confirmation":
            return {"error": "Step not awaiting confirmation"}
        step.status = "pending"
        step.confirmation_required = False
        wf.status = "running"
        return await self.execute_next_step(workflow_id)

    async def cancel_workflow(self, workflow_id: str) -> dict:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return {"error": "Workflow not found"}
        wf.status = "cancelled"
        return {"status": "cancelled", "workflow_id": workflow_id}


workflow_engine = WorkflowEngine()
