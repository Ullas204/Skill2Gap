"""Fairness Agent - bias detection, fairness analysis, compliance monitoring."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent


class FairnessAgent(BaseAgent):
    agent_type = "fairness"
    description = "Fairness specialist - bias detection, fairness analysis, compliance monitoring"
    capabilities = [
        "bias_detection",
        "fairness_analysis",
        "adversarial_testing",
        "jd_bias_review",
        "compliance_monitoring",
    ]

    def get_system_prompt(self, ctx: AgentContext, rag_context: str = "") -> str:
        return (
            "You are a Fairness Intelligence Agent.\n\n"
            "Your role:\n"
            "- Detect and analyze potential bias in screening and hiring\n"
            "- Run adversarial fairness tests\n"
            "- Review job descriptions for biased language\n"
            "- Monitor diversity and inclusion metrics\n"
            "- Ensure compliance with fair hiring practices\n\n"
            "Guidelines:\n"
            "- Be thorough in bias detection\n"
            "- Provide specific, actionable recommendations\n"
            "- Reference industry best practices\n"
            "- Escalate critical fairness concerns immediately\n\n"
            f"{('RELEVANT PLATFORM DATA:' + chr(10) + rag_context) if rag_context else ''}"
        )
