"""Analytics Agent - recruitment analytics, KPIs, predictive insights."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent


class AnalyticsAgent(BaseAgent):
    agent_type = "analytics"
    description = "Analytics specialist - recruitment metrics, KPIs, trends, predictive insights"
    capabilities = [
        "recruitment_analytics",
        "kpi_tracking",
        "trend_analysis",
        "predictive_insights",
        "report_generation",
    ]

    def get_system_prompt(self, ctx: AgentContext, rag_context: str = "") -> str:
        return (
            "You are an Analytics Intelligence Agent.\n\n"
            "Your role:\n"
            "- Generate comprehensive recruitment analytics\n"
            "- Track and report on key performance indicators\n"
            "- Identify trends and patterns in hiring data\n"
            "- Provide predictive insights for workforce planning\n"
            "- Create visual data summaries\n\n"
            "Guidelines:\n"
            "- Back all insights with real data\n"
            "- Highlight significant changes and anomalies\n"
            "- Provide context for metrics\n"
            "- Suggest data-driven actions\n\n"
            f"{('RELEVANT PLATFORM DATA:\\n' + rag_context) if rag_context else ''}"
        )
