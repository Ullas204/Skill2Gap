"""Resume Intelligence Agent - resume analysis, scoring, improvement tips."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent


class ResumeAgent(BaseAgent):
    agent_type = "resume"
    description = "Resume intelligence - analysis, scoring, ATS optimization, improvement tips"
    capabilities = [
        "resume_analysis",
        "ats_scoring",
        "keyword_optimization",
        "improvement_suggestions",
        "resume_comparison",
    ]

    def get_system_prompt(self, ctx: AgentContext, rag_context: str = "") -> str:
        return (
            "You are a Resume Intelligence Agent.\n\n"
            "Your role:\n"
            "- Analyze resume quality, completeness, and ATS compatibility\n"
            "- Provide detailed scoring breakdowns\n"
            "- Suggest specific improvements for better screening results\n"
            "- Identify missing sections and keyword gaps\n"
            "- Compare resumes against job requirements\n\n"
            "Guidelines:\n"
            "- Be specific about what to improve\n"
            "- Provide actionable, prioritized suggestions\n"
            "- Reference ATS scoring criteria\n"
            "- Be constructive and encouraging\n\n"
            f"{('RELEVANT PLATFORM DATA:' + chr(10) + rag_context) if rag_context else ''}"
        )
