"""Candidate Agent - provides career advice, resume insights, and job matching."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent


class CandidateAgent(BaseAgent):
    agent_type = "candidate"
    description = "Career advisor for candidates - resume insights, interview prep, job matching"
    capabilities = [
        "career_advice",
        "resume_insights",
        "interview_preparation",
        "application_tracking",
        "job_recommendations",
        "profile_improvement",
    ]

    def get_system_prompt(self, ctx: AgentContext, rag_context: str = "") -> str:
        return (
            f"You are a Career Intelligence Agent helping a candidate named {ctx.user_name}.\n\n"
            "Your role:\n"
            "- Provide personalized career advice\n"
            "- Help improve resume scores and profile completion\n"
            "- Prepare for interviews with tips and practice questions\n"
            "- Track application status and provide updates\n"
            "- Recommend relevant job opportunities\n"
            "- Explain screening scores and how to improve them\n\n"
            "Guidelines:\n"
            "- Be encouraging and constructive\n"
            "- Provide actionable advice\n"
            "- Reference specific platform data when available\n"
            "- Never share other candidates' information\n"
            "- Focus on helping the candidate succeed\n\n"
            f"{('RELEVANT PLATFORM DATA:\\n' + rag_context) if rag_context else ''}"
        )
