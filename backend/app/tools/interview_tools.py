"""Interview-related tools for the agent platform."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone, timedelta

from sqlalchemy import select

from app.db.session import async_session_factory
from app.domain.models import Interview, InterviewQuestion, InterviewScorecard, Job, User
from app.tools.registry import tool_registry


async def generate_interview_questions(
    job_id: str,
    categories: str = "technical,behavioral",
    difficulty: str = "medium",
    count: int = 5,
) -> dict:
    tech_qs = [
        "Explain the difference between REST and GraphQL. When would you use each?",
        "Describe your experience with microservices architecture. What challenges did you face?",
        "How do you ensure code quality in your team? What tools and practices do you use?",
        "Explain the concept of CI/CD and how you've implemented it in previous projects.",
        "Describe a complex debugging scenario you encountered and how you resolved it.",
        "What is your approach to database design and optimization?",
        "How do you handle technical debt in a fast-paced development environment?",
        "Explain event-driven architecture and give an example from your experience.",
    ]
    behavioral_qs = [
        "Tell me about a time you had to work with a difficult team member.",
        "Describe a situation where you had to make a critical decision under pressure.",
        "How do you handle competing priorities when multiple projects need your attention?",
        "Tell me about a time you failed. What did you learn from it?",
        "Describe your approach to mentoring junior team members.",
        "How do you stay updated with the latest technology trends?",
        "Tell me about a time you went above and beyond for a project.",
    ]

    cat_list = [c.strip() for c in categories.split(",")]
    questions = []
    idx = 0
    for _ in range(count):
        if "technical" in cat_list and idx < len(tech_qs):
            questions.append({"text": tech_qs[idx % len(tech_qs)], "category": "technical", "difficulty": difficulty})
            idx += 1
        if "behavioral" in cat_list and idx < len(behavioral_qs):
            questions.append({"text": behavioral_qs[idx % len(behavioral_qs)], "category": "behavioral", "difficulty": difficulty})
            idx += 1
        if len(questions) >= count:
            break

    return {"questions": questions[:count], "count": min(len(questions), count), "job_id": job_id}


async def schedule_interview(
    job_id: str,
    candidate_id: str,
    scheduled_at: str = "",
    interview_type: str = "recruiter_scheduled",
    duration_minutes: int = 60,
) -> dict:
    dt = datetime.now(timezone.utc) + timedelta(days=1)
    if scheduled_at:
        try:
            dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    async with async_session_factory() as db:
        interview = Interview(
            job_id=uuid.UUID(job_id),
            candidate_id=uuid.UUID(candidate_id),
            interview_type=interview_type,
            status="scheduled",
            scheduled_at=dt,
            duration_minutes=duration_minutes,
        )
        db.add(interview)
        await db.flush()
        await db.commit()
        return {
            "id": str(interview.id),
            "job_id": job_id,
            "candidate_id": candidate_id,
            "scheduled_at": dt.isoformat(),
            "status": "scheduled",
            "message": "Interview scheduled successfully.",
        }


async def get_interview_details(interview_id: str) -> dict:
    async with async_session_factory() as db:
        result = await db.execute(select(Interview).where(Interview.id == uuid.UUID(interview_id)))
        iv = result.scalar_one_or_none()
        if not iv:
            return {"error": "Interview not found"}

        q_stmt = select(InterviewQuestion).where(InterviewQuestion.interview_id == iv.id)
        questions = (await db.execute(q_stmt)).scalars().all()

        sc_stmt = select(InterviewScorecard).where(InterviewScorecard.interview_id == iv.id)
        scorecard = (await db.execute(sc_stmt)).scalar_one_or_none()

        return {
            "id": str(iv.id),
            "job_id": str(iv.job_id),
            "candidate_id": str(iv.candidate_id),
            "type": iv.interview_type,
            "status": iv.status,
            "scheduled_at": iv.scheduled_at.isoformat() if iv.scheduled_at else None,
            "questions_count": len(questions),
            "scorecard": {
                "overall_score": scorecard.overall_score,
                "recommendation": scorecard.recommendation,
            } if scorecard else None,
        }


async def get_interview_history(candidate_id: str = "", recruiter_id: str = "") -> dict:
    async with async_session_factory() as db:
        stmt = select(Interview)
        if candidate_id:
            stmt = stmt.where(Interview.candidate_id == uuid.UUID(candidate_id))
        elif recruiter_id:
            stmt = stmt.where(Interview.recruiter_id == uuid.UUID(recruiter_id))
        stmt = stmt.order_by(Interview.created_at.desc()).limit(20)
        result = await db.execute(stmt)
        interviews = result.scalars().all()

        return {
            "interviews": [
                {
                    "id": str(iv.id),
                    "job_id": str(iv.job_id),
                    "status": iv.status,
                    "type": iv.interview_type,
                    "scheduled_at": iv.scheduled_at.isoformat() if iv.scheduled_at else None,
                }
                for iv in interviews
            ],
            "count": len(interviews),
        }


def _register() -> None:
    tool_registry.register("generate_interview_questions", "Generate interview questions for a job", {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job UUID"},
            "categories": {"type": "string", "description": "Comma-separated: technical,behavioral,hr,coding"},
            "difficulty": {"type": "string", "description": "easy, medium, or hard"},
            "count": {"type": "integer", "description": "Number of questions", "default": 5},
        },
        "required": ["job_id"],
    }, generate_interview_questions, required_roles=["recruiter", "hr", "admin"])

    tool_registry.register("schedule_interview", "Schedule an interview with a candidate", {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job UUID"},
            "candidate_id": {"type": "string", "description": "Candidate user UUID"},
            "scheduled_at": {"type": "string", "description": "ISO datetime string"},
            "interview_type": {"type": "string", "description": "recruiter_scheduled or mock"},
            "duration_minutes": {"type": "integer", "description": "Duration in minutes", "default": 60},
        },
        "required": ["job_id", "candidate_id"],
    }, schedule_interview, required_roles=["recruiter", "admin"])

    tool_registry.register("get_interview_details", "Get detailed information about an interview", {
        "type": "object",
        "properties": {
            "interview_id": {"type": "string", "description": "Interview UUID"},
        },
        "required": ["interview_id"],
    }, get_interview_details, required_roles=["recruiter", "hr", "admin", "candidate"])

    tool_registry.register("get_interview_history", "Get interview history for a candidate or recruiter", {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string", "description": "Candidate user UUID"},
            "recruiter_id": {"type": "string", "description": "Recruiter user UUID"},
        },
    }, get_interview_history, required_roles=["recruiter", "hr", "admin", "candidate"])
