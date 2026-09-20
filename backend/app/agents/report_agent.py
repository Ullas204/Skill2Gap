"""Report Generation Agent - creates various HR/reports."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent


class ReportAgent(BaseAgent):
    agent_type = "report"
    description = "Report generation - hiring reports, candidate reports, executive summaries"
    capabilities = [
        "hiring_report",
        "candidate_report",
        "interview_report",
        "fairness_report",
        "executive_summary",
        "export_pdf",
    ]

    def get_system_prompt(self, ctx: AgentContext, rag_context: str = "") -> str:
        return (
            "You are a Report Generation Agent.\n\n"
            "Your role:\n"
            "- Generate comprehensive hiring, candidate, and interview reports\n"
            "- Create executive summaries for leadership\n"
            "- Compile fairness and compliance reports\n"
            "- Export reports in various formats (PDF, CSV)\n\n"
            "Guidelines:\n"
            "- Structure reports clearly with sections\n"
            "- Include key metrics and insights\n"
            "- Provide both summary and detailed views\n"
            "- Cite data sources\n\n"
            f"{('RELEVANT PLATFORM DATA:' + chr(10) + rag_context) if rag_context else ''}"
        )
