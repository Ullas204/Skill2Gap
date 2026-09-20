"""Job Matching Agent - finds best job-candidate matches."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent


class JobMatchingAgent(BaseAgent):
    agent_type = "job_matching"
    description = "Job matching - finds best job-candidate fit, skill gap analysis"
    capabilities = [
        "job_candidate_matching",
        "skill_gap_analysis",
        "match_scoring",
        "recommendation",
    ]

    def get_system_prompt(self, ctx: AgentContext, rag_context: str = "") -> str:
        return (
            "You are a Job Matching Intelligence Agent.\n\n"
            "Your role:\n"
            "- Match candidates to jobs based on skills, experience, and preferences\n"
            "- Analyze skill gaps between candidates and job requirements\n"
            "- Provide match scores with detailed explanations\n"
            "- Recommend career paths and upskilling opportunities\n\n"
            "Guidelines:\n"
            "- Use actual platform data for matching\n"
            "- Consider both required and preferred skills\n"
            "- Factor in experience level and education\n"
            "- Provide actionable improvement suggestions\n\n"
            f"{('RELEVANT PLATFORM DATA:\\n' + rag_context) if rag_context else ''}"
        )
