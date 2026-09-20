"""Candidate-related tools for the agent platform."""

from __future__ import annotations

import uuid

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.domain.models import (
    CandidateProfile, User, UserRole, Skill, CandidateSkill,
    ScreeningResult, CandidateRanking, JobApplication, Resume, ResumeAnalysis,
)
from app.tools.registry import tool_registry


async def search_candidates(query: str = "", skills: str = "", location: str = "", top_k: int = 10) -> dict:
    async with async_session_factory() as db:
        stmt = (
            select(CandidateProfile, User)
            .join(User, CandidateProfile.user_id == User.id)
            .where(User.is_active == True)
        )
        if location:
            stmt = stmt.where(CandidateProfile.location.ilike(f"%{location}%"))
        if query:
            stmt = stmt.where(
                CandidateProfile.current_role.ilike(f"%{query}%")
                | CandidateProfile.bio.ilike(f"%{query}%")
            )
        stmt = stmt.limit(top_k)
        result = await db.execute(stmt)
        rows = result.all()

        candidates = []
        for profile, user in rows:
            skill_stmt = (
                select(Skill.name, CandidateSkill.proficiency, CandidateSkill.years_of_experience)
                .join(CandidateSkill, Skill.id == CandidateSkill.skill_id)
                .where(CandidateSkill.profile_id == profile.id)
            )
            skills_result = await db.execute(skill_stmt)
            skill_list = [
                {"name": s[0], "proficiency": s[1], "years": s[2]}
                for s in skills_result.all()
            ]
            candidates.append({
                "id": str(user.id),
                "name": user.full_name,
                "email": user.email,
                "current_role": profile.current_role,
                "location": profile.location,
                "profile_completion": profile.profile_completion,
                "skills": skill_list,
            })
    return {"candidates": candidates, "count": len(candidates)}


async def rank_candidates(job_id: str) -> dict:
    async with async_session_factory() as db:
        stmt = (
            select(CandidateRanking, User)
            .join(User, CandidateRanking.candidate_id == User.id)
            .where(CandidateRanking.job_id == uuid.UUID(job_id))
            .order_by(CandidateRanking.rank)
            .limit(20)
        )
        result = await db.execute(stmt)
        rows = result.all()

        ranked = []
        for ranking, user in rows:
            ranked.append({
                "id": str(user.id),
                "name": user.full_name,
                "rank": ranking.rank,
                "overall_score": ranking.overall_score,
                "strength_level": ranking.strength_level,
            })
    return {"rankings": ranked, "count": len(ranked), "job_id": job_id}


async def explain_candidate_score(candidate_id: str, job_id: str) -> dict:
    async with async_session_factory() as db:
        stmt = select(ScreeningResult).where(
            ScreeningResult.candidate_id == uuid.UUID(candidate_id),
            ScreeningResult.job_id == uuid.UUID(job_id),
        )
        result = await db.execute(stmt)
        sr = result.scalar_one_or_none()

        if not sr:
            return {"error": "No screening result found for this candidate and job"}

        return {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "overall_score": sr.overall_match_score,
            "breakdown": {
                "skill_match": sr.skill_match_score,
                "experience_match": sr.experience_match_score,
                "education_match": sr.education_match_score,
                "project_match": sr.project_match_score,
                "certification_match": sr.certification_match_score,
                "location_match": sr.location_match_score,
                "semantic_match": sr.semantic_match_score,
            },
            "matched_skills": sr.matched_skills or [],
            "missing_skills": sr.missing_required_skills or [],
            "strengths": sr.strengths or [],
            "weaknesses": sr.weaknesses or [],
            "recommendation": sr.recommendation,
        }


async def compare_candidates(candidate_ids: str, job_id: str) -> dict:
    ids = [cid.strip() for cid in candidate_ids.split(",")]
    comparisons = []
    for cid in ids:
        result = await explain_candidate_score(cid, job_id)
        if "error" not in result:
            comparisons.append(result)
    comparisons.sort(key=lambda x: x.get("overall_score", 0), reverse=True)
    return {"comparisons": comparisons, "job_id": job_id, "count": len(comparisons)}


async def get_candidate_profile(candidate_id: str) -> dict:
    async with async_session_factory() as db:
        stmt = (
            select(CandidateProfile, User)
            .join(User, CandidateProfile.user_id == User.id)
            .where(User.id == uuid.UUID(candidate_id))
        )
        result = await db.execute(stmt)
        row = result.one_or_none()
        if not row:
            return {"error": "Candidate not found"}

        profile, user = row
        skill_stmt = (
            select(Skill.name, CandidateSkill.proficiency, CandidateSkill.years_of_experience)
            .join(CandidateSkill, Skill.id == CandidateSkill.skill_id)
            .where(CandidateSkill.profile_id == profile.id)
        )
        skills_result = await db.execute(skill_stmt)
        skills = [{"name": s[0], "proficiency": s[1], "years": s[2]} for s in skills_result.all()]

        return {
            "id": str(user.id),
            "name": user.full_name,
            "email": user.email,
            "current_role": profile.current_role,
            "location": profile.location,
            "bio": profile.bio,
            "profile_completion": profile.profile_completion,
            "skills": skills,
            "linkedin": profile.linkedin_url,
            "github": profile.github_url,
        }


def _register() -> None:
    tool_registry.register("search_candidates", "Search for candidates by skills, role, or location", {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query for role or keywords"},
            "skills": {"type": "string", "description": "Comma-separated skill names"},
            "location": {"type": "string", "description": "Location filter"},
            "top_k": {"type": "integer", "description": "Number of results", "default": 10},
        },
    }, search_candidates, required_roles=["recruiter", "hr", "admin"])

    tool_registry.register("rank_candidates", "Rank candidates for a specific job", {
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Job UUID"},
        },
        "required": ["job_id"],
    }, rank_candidates, required_roles=["recruiter", "hr", "admin"])

    tool_registry.register("explain_candidate_score", "Explain why a candidate received a specific screening score", {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string", "description": "Candidate user UUID"},
            "job_id": {"type": "string", "description": "Job UUID"},
        },
        "required": ["candidate_id", "job_id"],
    }, explain_candidate_score, required_roles=["recruiter", "hr", "admin", "candidate"])

    tool_registry.register("compare_candidates", "Compare multiple candidates side by side for a job", {
        "type": "object",
        "properties": {
            "candidate_ids": {"type": "string", "description": "Comma-separated candidate UUIDs"},
            "job_id": {"type": "string", "description": "Job UUID"},
        },
        "required": ["candidate_ids", "job_id"],
    }, compare_candidates, required_roles=["recruiter", "hr", "admin"])

    tool_registry.register("get_candidate_profile", "Get detailed candidate profile information", {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string", "description": "Candidate user UUID"},
        },
        "required": ["candidate_id"],
    }, get_candidate_profile, required_roles=["recruiter", "hr", "admin", "candidate"])
