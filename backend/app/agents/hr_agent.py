"""HR Agent - hiring analytics, fairness monitoring, policy guidance."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent


class HRAgent(BaseAgent):
    agent_type = "hr"
    description = "HR specialist - hiring analytics, fairness monitoring, compliance, policy guidance"
    capabilities = [
        "hiring_analytics",
        "fairness_monitoring",
        "compliance_checking",
        "policy_guidance",
        "report_generation",
        "recruiter_performance",
        "headcount_planning",
    ]

    def get_system_prompt(self, ctx: AgentContext, rag_context: str = "") -> str:
        return (
            f"You are an HR Intelligence Agent assisting {ctx.user_name}.\n\n"
            "Your role:\n"
            "- Generate comprehensive hiring reports and analytics\n"
            "- Monitor recruitment fairness and detect potential bias\n"
            "- Ensure compliance with hiring policies\n"
            "- Track recruiter performance and pipeline health\n"
            "- Provide strategic workforce planning insights\n"
            "- Generate executive summaries\n\n"
            "Guidelines:\n"
            "- Focus on data-driven insights\n"
            "- Highlight any fairness or bias concerns\n"
            "- Provide actionable recommendations\n"
            "- Support decisions with metrics\n"
            "- Generate reports on demand\n\n"
            f"{('RELEVANT PLATFORM DATA:\\n' + rag_context) if rag_context else ''}"
        )
