"""Initialize and register all agents with the orchestrator."""

from app.agents.base import orchestrator
from app.agents.candidate_agent import CandidateAgent
from app.agents.recruiter_agent import RecruiterAgent
from app.agents.hr_agent import HRAgent
from app.agents.admin_agent import AdminAgent
from app.agents.resume_agent import ResumeAgent
from app.agents.job_matching_agent import JobMatchingAgent
from app.agents.interview_agent import InterviewAgent
from app.agents.analytics_agent import AnalyticsAgent
from app.agents.fairness_agent import FairnessAgent
from app.agents.report_agent import ReportAgent


def register_all_agents() -> None:
    orchestrator.register(CandidateAgent())
    orchestrator.register(RecruiterAgent())
    orchestrator.register(HRAgent())
    orchestrator.register(AdminAgent())
    orchestrator.register(ResumeAgent())
    orchestrator.register(JobMatchingAgent())
    orchestrator.register(InterviewAgent())
    orchestrator.register(AnalyticsAgent())
    orchestrator.register(FairnessAgent())
    orchestrator.register(ReportAgent())
