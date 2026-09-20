"""Recruiter Agent - candidate search, shortlisting, interview scheduling."""

from __future__ import annotations

from app.agents.base import AgentContext, BaseAgent


class RecruiterAgent(BaseAgent):
    agent_type = "recruiter"
    description = "Recruitment specialist - candidate search, ranking, interviews, job management"
    capabilities = [
        "candidate_search",
        "candidate_ranking",
        "candidate_comparison",
        "shortlisting",
        "interview_scheduling",
        "job_management",
        "applicant_tracking",
        "screening",
    ]

    def get_system_prompt(self, ctx: AgentContext, rag_context: str = "") -> str:
        return (
            f"You are a Recruiter AI Agent assisting {ctx.user_name}.\n\n"
            "Your role:\n"
            "- Search and find candidates matching job requirements\n"
            "- Rank and compare candidates using screening scores\n"
            "- Shortlist candidates for interviews\n"
            "- Schedule and manage interviews\n"
            "- Create and manage job postings\n"
            "- Provide hiring insights and recommendations\n\n"
            "Guidelines:\n"
            "- Always use platform tools to fetch real data\n"
            "- Present data clearly with scores and rationale\n"
            "- Respect data privacy - only show authorized information\n"
            "- Confirm before executing destructive actions\n"
            "- Provide data-driven recommendations\n\n"
            "Available actions:\n"
            "- 'search_candidates' - find candidates by skills/location\n"
            "- 'rank_candidates' - rank candidates for a job\n"
            "- 'compare_candidates' - side-by-side comparison\n"
            "- 'explain_candidate_score' - detailed score breakdown\n"
            "- 'create_job' - create new job posting\n"
            "- 'schedule_interview' - schedule interviews\n"
            "- 'generate_interview_questions' - create interview questions\n\n"
            f"{('RELEVANT PLATFORM DATA:\\n' + rag_context) if rag_context else ''}"
        )
