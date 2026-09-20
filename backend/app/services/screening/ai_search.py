from __future__ import annotations

import logging
import uuid

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.models import (
    CandidateProfile,
    CandidateRanking,
    CandidateSkill,
    Certification,
    Education,
    Experience,
    Job,
    JobApplication,
    ParsedResumeData,
    Project,
    Resume,
    ScreeningResult,
    Skill,
    User,
)
from app.repositories.candidate.profile import CandidateProfileRepository
from app.repositories.candidate.resume import ParsedResumeDataRepository, ResumeRepository
from app.repositories.jobs.job import JobApplicationRepository, JobRepository
from app.repositories.screening.screening import ScreeningResultRepository
from app.services.screening.matching_engine import MatchingEngine
from app.services.screening.skill_graph import SkillGraph

logger = logging.getLogger(__name__)


class AISearchService:
    """Natural language AI search for candidates across jobs."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.screening_repo = ScreeningResultRepository(session)
        self.profile_repo = CandidateProfileRepository(session)
        self.resume_repo = ResumeRepository(session)
        self.parsed_repo = ParsedResumeDataRepository(session)
        self.job_repo = JobRepository(session)
        self.app_repo = JobApplicationRepository(session)

    async def search_candidates(
        self,
        query: str,
        recruiter_id: uuid.UUID | None = None,
        job_id: uuid.UUID | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> dict:
        parsed = SkillGraph.parse_search_query(query)
        query_skills = parsed.get("skills", [])
        query_years = parsed.get("experience_years")
        query_location = parsed.get("location")
        query_employment_type = parsed.get("employment_type")

        if job_id:
            return await self._search_for_job(
                job_id, recruiter_id, query_skills, query_years,
                query_location, limit, offset,
            )
        return await self._search_global(
            query_skills, query_years, query_location,
            query_employment_type, limit, offset,
        )

    async def _search_for_job(
        self,
        job_id: uuid.UUID,
        recruiter_id: uuid.UUID | None,
        query_skills: list[str],
        query_years: float | None,
        query_location: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        if recruiter_id:
            job = await self.job_repo.get_by_recruiter(job_id, recruiter_id)
        else:
            job = await self.session.get(Job, job_id)
        if not job:
            return {"results": [], "total": 0, "query_skills": query_skills}

        applications = await self.app_repo.list_by_job(job_id)
        candidate_ids = [app.candidate_id for app in applications]

        results = []
        for cid in candidate_ids:
            screening = await self.screening_repo.get_by_job_and_candidate(job_id, cid)
            profile = await self.profile_repo.get_by_user_id(cid)
            user = await self.session.get(User, cid)
            if not profile or not user:
                continue

            candidate_skills = await self._get_skill_names(profile)
            experiences = await self._get_experiences(profile)
            candidate_years = self._calc_experience(experiences)

            relevance = MatchingEngine.calculate_search_relevance(
                candidate_skills=candidate_skills,
                query_skills=query_skills,
                candidate_years=candidate_years,
                query_years=query_years,
                candidate_location=profile.location,
                query_location=query_location,
            )

            results.append({
                "candidate_id": str(cid),
                "candidate_name": user.full_name,
                "candidate_email": user.email,
                "overall_score": screening.overall_match_score if screening else 0,
                "relevance_score": relevance,
                "matched_skills": screening.matched_skills if screening else [],
                "missing_skills": screening.missing_required_skills if screening else [],
                "recommendation": screening.recommendation if screening else "not_screened",
                "strength_level": screening.strength_level if screening else "low",
                "experience_years": candidate_years,
                "location": profile.location or "",
                "has_screening": screening is not None,
            })

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        total = len(results)
        paginated = results[offset:offset + limit]

        return {
            "results": paginated,
            "total": total,
            "query_skills": query_skills,
            "query_years": query_years,
            "query_location": query_location,
            "job_id": str(job_id),
            "job_title": job.title,
        }

    async def _search_global(
        self,
        query_skills: list[str],
        query_years: float | None,
        query_location: str | None,
        query_employment_type: str | None,
        limit: int,
        offset: int,
    ) -> dict:
        stmt = (
            select(CandidateProfile)
            .options(
                joinedload(CandidateProfile.user),
                joinedload(CandidateProfile.candidate_skills).joinedload(CandidateSkill.skill),
                joinedload(CandidateProfile.experiences),
            )
        )
        result = await self.session.execute(stmt)
        profiles = list(result.unique().scalars().all())

        results = []
        for profile in profiles:
            user = profile.user
            if not user or not user.is_active:
                continue

            candidate_skills = [cs.skill.name for cs in profile.candidate_skills if cs.skill]
            experiences = [
                {"start_date": str(e.start_date) if e.start_date else "",
                 "end_date": str(e.end_date) if e.end_date else "",
                 "is_current": e.is_current}
                for e in profile.experiences
            ]
            candidate_years = self._calc_experience(experiences)

            relevance = MatchingEngine.calculate_search_relevance(
                candidate_skills=candidate_skills,
                query_skills=query_skills,
                candidate_years=candidate_years,
                query_years=query_years,
                candidate_location=profile.location,
                query_location=query_location,
            )

            if relevance < 20 and query_skills:
                continue

            results.append({
                "candidate_id": str(user.id),
                "candidate_name": user.full_name,
                "candidate_email": user.email,
                "relevance_score": relevance,
                "skills": candidate_skills[:10],
                "experience_years": candidate_years,
                "location": profile.location or "",
                "current_role": profile.current_role or "",
                "profile_completion": profile.profile_completion,
            })

        results.sort(key=lambda x: x["relevance_score"], reverse=True)
        total = len(results)
        paginated = results[offset:offset + limit]

        return {
            "results": paginated,
            "total": total,
            "query_skills": query_skills,
            "query_years": query_years,
            "query_location": query_location,
        }

    async def _get_skill_names(self, profile: CandidateProfile) -> list[str]:
        stmt = (
            select(Skill.name)
            .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
            .where(CandidateSkill.profile_id == profile.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _get_experiences(self, profile: CandidateProfile) -> list[dict]:
        stmt = select(Experience).where(Experience.profile_id == profile.id)
        result = await self.session.execute(stmt)
        exps = result.scalars().all()
        return [
            {"start_date": str(e.start_date) if e.start_date else "",
             "end_date": str(e.end_date) if e.end_date else "",
             "is_current": e.is_current}
            for e in exps
        ]

    @staticmethod
    def _calc_experience(experiences: list[dict]) -> float:
        from datetime import date
        total_months = 0.0
        for exp in experiences:
            start_str = exp.get("start_date", "")
            end_str = exp.get("end_date", "")
            is_current = exp.get("is_current", False)
            if not start_str:
                continue
            try:
                parts = start_str.split("-")
                start = date(int(parts[0]), int(parts[1]), int(parts[2]))
                if is_current:
                    end = date.today()
                elif end_str:
                    parts2 = end_str.split("-")
                    end = date(int(parts2[0]), int(parts2[1]), int(parts2[2]))
                else:
                    continue
                delta_months = (end.year - start.year) * 12 + (end.month - start.month)
                total_months += max(delta_months, 0)
            except (ValueError, IndexError):
                continue
        return round(total_months / 12, 1)
