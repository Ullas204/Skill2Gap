"""Job-related tools for the agent platform."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.domain.models import Job, JobApplication, User
from app.tools.registry import tool_registry


async def search_jobs(query: str = "", location: str = "", status: str = "published", top_k: int = 10) -> dict:
    async with async_session_factory() as db:
        stmt = select(Job).where(Job.is_archived == False)
        if status:
            stmt = stmt.where(Job.status == status)
        if query:
            stmt = stmt.where(
                Job.title.ilike(f"%{query}%")
                | Job.description.ilike(f"%{query}%")
                | Job.company.ilike(f"%{query}%")
            )
        if location:
            stmt = stmt.where(Job.location.ilike(f"%{location}%"))
        stmt = stmt.order_by(Job.created_at.desc()).limit(top_k)
        result = await db.execute(stmt)
        jobs = result.scalars().all()

        return {
            "jobs": [
                {
                    "id": str(j.id),
                    "title": j.title,
                    "company": j.company,
                    "department": j.department,
                    "location": j.location,
                    "employment_type": j.employment_type,
                    "status": j.status,
                    "required_skills": j.required_skills,
                    "salary_min": j.salary_min,
                    "salary_max": j.salary_max,
                }
                for j in jobs
            ],
            "count": len(jobs),
        }


async def get_job_details(job_id: str) -> dict:
    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
        job = result.scalar_one_or_none()
        if not job:
            return {"error": "Job not found"}

        app_count_stmt = select(JobApplication).where(JobApplication.job_id == job.id)
        apps = (await db.execute(app_count_stmt)).scalars().all()

        return {
            "id": str(job.id),
            "title": job.title,
            "company": job.company,
            "department": job.department,
            "location": job.location,
            "employment_type": job.employment_type,
            "status": job.status,
            "description": job.description[:1000],
            "required_skills": job.required_skills,
            "preferred_skills": job.preferred_skills,
            "experience_required": job.experience_required,
            "education_required": job.education_required,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "application_count": len(apps),
        }


async def create_job(
    title: str,
    company: str,
    location: str,
    employment_type: str = "full_time",
    description: str = "",
    required_skills: str = "",
    recruiter_id: str = "",
) -> dict:
    skills = [s.strip() for s in required_skills.split(",") if s.strip()] if required_skills else []
    async with async_session_factory() as db:
        job = Job(
            recruiter_id=uuid.UUID(recruiter_id) if recruiter_id else uuid.uuid4(),
            title=title,
            company=company,
            location=location,
            employment_type=employment_type,
            description=description or f"We are hiring for {title} at {company}.",
            required_skills=skills,
            status="draft",
        )
        db.add(job)
        await db.flush()
        await db.commit()
        return {
            "id": str(job.id),
            "title": job.title,
            "status": job.status,
            "message": f"Job '{job.title}' created successfully as draft.",
        }


async def update_job_status(job_id: str, status: str) -> dict:
    valid = ["draft", "published", "closed", "archived"]
    if status not in valid:
        return {"error": f"Invalid status. Must be one of: {', '.join(valid)}"}
    async with async_session_factory() as db:
        result = await db.execute(select(Job).where(Job.id == uuid.UUID(job_id)))
        job = result.scalar_one_or_none()
        if not job:
            return {"error": "Job not found"}
        job.status = status
        await db.commit()
        return {"id": str(job.id), "title": job.title, "status": status, "message": f"Job status updated to {status}."}


async def get_job_applicants(job_id: str) -> dict:
    async with async_session_factory() as db:
        stmt = (
            select(JobApplication, User)
            .join(User, JobApplication.candidate_id == User.id)
            .where(JobApplication.job_id == uuid.UUID(job_id))
        )
        result = await db.execute(stmt)
        rows = result.all()

        applicants = []
        for app, user in rows:
            applicants.append({
                "id": str(user.id),
                "name": user.full_name,
                "email": user.email,
                "application_status": app.status,
                "applied_at": app.created_at.isoformat() if app.created_at else None,
            })
    return {"applicants": applicants, "count": len(applicants), "job_id": job_id}


def _register() -> None:
    tool_registry.register("search_jobs", "Search for open job positions", {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query for title or keywords"},
            "location": {"type": "string", "description": "Location filter"},
            "status": {"type": "string", "description": "Job status filter", "default": "published"},
            "top_k": {"type": "integer", "description": "Number of results", "default": 10},
        },
    }, search_jobs, required_roles=["candidate", "recruiter", "hr", "admin"])

    tool_registry.register("get_job_details", "Get detailed information about a specific job", {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job UUID"},
        },
        "required": ["job_id"],
    }, get_job_details, required_roles=["candidate", "recruiter", "hr", "admin"])

    tool_registry.register("create_job", "Create a new job posting", {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Job title"},
            "company": {"type": "string", "description": "Company name"},
            "location": {"type": "string", "description": "Job location"},
            "employment_type": {"type": "string", "description": "Type: full_time, part_time, contract, internship"},
            "description": {"type": "string", "description": "Job description"},
            "required_skills": {"type": "string", "description": "Comma-separated required skills"},
        },
        "required": ["title", "company", "location"],
    }, create_job, required_roles=["recruiter", "admin"])

    tool_registry.register("update_job_status", "Update a job's status (draft/published/closed/archived)", {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job UUID"},
            "status": {"type": "string", "description": "New status"},
        },
        "required": ["job_id", "status"],
    }, update_job_status, required_roles=["recruiter", "admin"])

    tool_registry.register("get_job_applicants", "Get list of applicants for a job", {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job UUID"},
        },
        "required": ["job_id"],
    }, get_job_applicants, required_roles=["recruiter", "hr", "admin"])
