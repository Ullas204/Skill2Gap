"""Interview Agent - interview preparation, question generation, evaluation."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent


class InterviewAgent(BaseAgent):
    agent_type = "interview"
    description = "Interview specialist - question generation, scheduling, evaluation, coaching"
    capabilities = [
        "question_generation",
        "interview_scheduling",
        "evaluation_assistance",
        "candidate_coaching",
        "scorecard_analysis",
    ]

    def get_system_prompt(self, ctx: AgentContext, rag_context: str = "") -> str:
        return (
            "You are an Interview Intelligence Agent.\n\n"
            "Your role:\n"
            "- Generate tailored interview questions for specific roles\n"
            "- Help schedule and manage interviews\n"
            "- Provide evaluation frameworks and scorecards\n"
            "- Coach candidates on interview preparation\n"
            "- Analyze interview performance and provide feedback\n\n"
            "Guidelines:\n"
            "- Generate role-appropriate questions\n"
            "- Consider difficulty levels and question categories\n"
            "- Provide structured evaluation criteria\n"
            "- Be supportive when coaching candidates\n\n"
            f"{('RELEVANT PLATFORM DATA:' + chr(10) + rag_context) if rag_context else ''}"
        )
