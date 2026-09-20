"""Analytics-related tools for the agent platform."""

from __future__ import annotations

import uuid

from sqlalchemy import select, func

from app.db.session import async_session_factory
from app.domain.models import (
    Job, JobApplication, User, UserRole, ScreeningResult,
    Interview, AuditLog,
)
from app.tools.registry import tool_registry


async def generate_analytics_report(report_type: str = "hiring", parameters: str = "") -> dict:
    async with async_session_factory() as db:
        if report_type == "hiring":
            total_jobs = (await db.execute(select(func.count(Job.id)))).scalar() or 0
            active_jobs = (await db.execute(
                select(func.count(Job.id)).where(Job.status == "published")
            )).scalar() or 0
            total_apps = (await db.execute(select(func.count(JobApplication.id)))).scalar() or 0
            total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
            return {
                "report_type": "hiring_overview",
                "total_jobs": total_jobs,
                "active_jobs": active_jobs,
                "total_applications": total_apps,
                "total_users": total_users,
                "summary": f"Hiring overview: {active_jobs} active jobs out of {total_jobs} total, {total_apps} applications received.",
            }

        elif report_type == "pipeline":
            statuses = {}
            for status in ["applied", "under_review", "shortlisted", "interview_scheduled", "offered", "hired", "rejected"]:
                count = (await db.execute(
                    select(func.count(JobApplication.id)).where(JobApplication.status == status)
                )).scalar() or 0
                statuses[status] = count
            return {"report_type": "pipeline", "pipeline": statuses, "summary": f"Pipeline breakdown: {statuses}"}

        elif report_type == "candidates":
            total = (await db.execute(select(func.count(User.id)))).scalar() or 0
            screened = (await db.execute(select(func.count(ScreeningResult.id)))).scalar() or 0
            return {"report_type": "candidate_overview", "total_users": total, "screened": screened}

        return {"report_type": report_type, "message": f"Report type '{report_type}' generated with parameters: {parameters}"}


async def get_system_health() -> dict:
    async with async_session_factory() as db:
        total_users = (await db.execute(select(func.count(User.id)))).scalar() or 0
        active_users = (await db.execute(
            select(func.count(User.id)).where(User.is_active == True)
        )).scalar() or 0
        total_jobs = (await db.execute(select(func.count(Job.id)))).scalar() or 0
        total_audits = (await db.execute(select(func.count(AuditLog.id)))).scalar() or 0
        failed_logins = (await db.execute(
            select(func.count(AuditLog.id)).where(
                AuditLog.action == "login", AuditLog.success == False
            )
        )).scalar() or 0

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_jobs": total_jobs,
            "total_audit_events": total_audits,
            "failed_logins": failed_logins,
            "status": "healthy" if failed_logins < 50 else "warning",
        }


async def search_skills(query: str = "") -> dict:
    async with async_session_factory() as db:
        from app.domain.models import Skill
        stmt = select(Skill)
        if query:
            stmt = stmt.where(Skill.name.ilike(f"%{query}%"))
        stmt = stmt.limit(50)
        result = await db.execute(stmt)
        skills = result.scalars().all()
        return {
            "skills": [{"id": s.id, "name": s.name, "category": s.category} for s in skills],
            "count": len(skills),
        }


def _register() -> None:
    tool_registry.register("generate_analytics_report", "Generate analytics reports (hiring, pipeline, candidates)", {
        "type": "object",
        "properties": {
            "report_type": {"type": "string", "description": "Type: hiring, pipeline, candidates"},
            "parameters": {"type": "string", "description": "Additional parameters"},
        },
        "required": ["report_type"],
    }, generate_analytics_report, required_roles=["recruiter", "hr", "admin"])

    tool_registry.register("get_system_health", "Get platform system health metrics", {
        "type": "object",
        "properties": {},
    }, get_system_health, required_roles=["admin"])

    tool_registry.register("search_skills", "Search available skills in the platform", {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Skill search query"},
        },
    }, search_skills, required_roles=["candidate", "recruiter", "hr", "admin"])
