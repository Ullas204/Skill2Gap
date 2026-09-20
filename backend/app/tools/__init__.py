"""Register all tool modules."""

from app.tools import candidate_tools, job_tools, interview_tools, analytics_tools, fairness_tools, report_tools


def register_all_tools() -> None:
    candidate_tools._register()
    job_tools._register()
    interview_tools._register()
    analytics_tools._register()
    fairness_tools._register()
    report_tools._register()
