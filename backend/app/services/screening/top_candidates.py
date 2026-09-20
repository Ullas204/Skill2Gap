from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    CandidateProfile,
    CandidateRanking,
    Job,
    JobApplication,
    ScreeningResult,
    SkillGapAnalysis,
    User,
)
from app.repositories.candidate.profile import CandidateProfileRepository
from app.repositories.jobs.job import JobApplicationRepository, JobRepository
from app.repositories.screening.screening import (
    CandidateRankingRepository,
    ScreeningResultRepository,
    SkillGapAnalysisRepository,
)

logger = logging.getLogger(__name__)


class TopCandidatesService:
    """Service for retrieving top candidates across jobs and generating
    hiring recommendations with detailed explanations."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.screening_repo = ScreeningResultRepository(session)
        self.ranking_repo = CandidateRankingRepository(session)
        self.skill_gap_repo = SkillGapAnalysisRepository(session)
        self.profile_repo = CandidateProfileRepository(session)
        self.job_repo = JobRepository(session)
        self.app_repo = JobApplicationRepository(session)

    async def get_top_candidates(
        self,
        recruiter_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        if job_id:
            return await self._get_top_for_job(recruiter_id, job_id, limit)
        return await self._get_top_across_jobs(recruiter_id, limit)

    async def _get_top_for_job(
        self,
        recruiter_id: uuid.UUID,
        job_id: uuid.UUID,
        limit: int,
    ) -> dict[str, Any]:
        job = await self.job_repo.get_by_recruiter(job_id, recruiter_id)
        if not job:
            return {"error": "Job not found or access denied"}

        rankings = await self.ranking_repo.list_by_job(job_id)
        top = rankings[:limit]

        candidates = []
        for r in top:
            user = await self.session.get(User, r.candidate_id)
            screening = await self.screening_repo.get_by_job_and_candidate(
                job_id, r.candidate_id,
            )
            candidates.append({
                "rank": r.rank,
                "candidate_id": str(r.candidate_id),
                "candidate_name": user.full_name if user else "",
                "candidate_email": user.email if user else "",
                "overall_score": r.overall_score,
                "strength_level": r.strength_level,
                "recommendation": screening.recommendation if screening else "consider",
                "skill_match": screening.skill_match_score if screening else 0,
                "experience_match": screening.experience_match_score if screening else 0,
                "matched_skills": screening.matched_skills if screening else [],
                "rank_change": r.rank_change,
            })

        return {
            "job_id": str(job_id),
            "job_title": job.title,
            "candidates": candidates,
            "total_ranked": len(rankings),
        }

    async def _get_top_across_jobs(
        self,
        recruiter_id: uuid.UUID,
        limit: int,
    ) -> dict[str, Any]:
        jobs = await self.job_repo.list_by_recruiter(recruiter_id)
        all_candidates: list[dict] = []

        for job in jobs:
            rankings = await self.ranking_repo.list_by_job(job.id)
            for r in rankings[:5]:
                user = await self.session.get(User, r.candidate_id)
                screening = await self.screening_repo.get_by_job_and_candidate(
                    job.id, r.candidate_id,
                )
                all_candidates.append({
                    "job_id": str(job.id),
                    "job_title": job.title,
                    "rank": r.rank,
                    "candidate_id": str(r.candidate_id),
                    "candidate_name": user.full_name if user else "",
                    "candidate_email": user.email if user else "",
                    "overall_score": r.overall_score,
                    "strength_level": r.strength_level,
                    "recommendation": screening.recommendation if screening else "consider",
                    "matched_skills": screening.matched_skills if screening else [],
                })

        all_candidates.sort(key=lambda x: -x["overall_score"])
        return {
            "candidates": all_candidates[:limit],
            "total_jobs": len(jobs),
        }

    async def get_hiring_recommendation(
        self,
        job_id: uuid.UUID,
        candidate_id: uuid.UUID,
    ) -> dict[str, Any]:
        screening = await self.screening_repo.get_by_job_and_candidate(job_id, candidate_id)
        if not screening:
            return {"error": "No screening result found"}

        job = await self.session.get(Job, job_id)
        user = await self.session.get(User, candidate_id)
        gap = await self.skill_gap_repo.get_by_screening_result(screening.id)

        explanation = self._build_recommendation_explanation(screening, gap, job)

        return {
            "job_id": str(job_id),
            "job_title": job.title if job else "",
            "candidate_id": str(candidate_id),
            "candidate_name": user.full_name if user else "",
            "recommendation": screening.recommendation,
            "overall_score": screening.overall_match_score,
            "confidence_score": screening.semantic_match_score,
            "strength_level": screening.strength_level,
            "explanation": explanation,
            "matched_skills": screening.matched_skills or [],
            "missing_skills": screening.missing_required_skills or [],
            "strengths": screening.strengths or [],
            "weaknesses": screening.weaknesses or [],
            "interview_readiness": gap.interview_readiness_score if gap else None,
            "improvement_suggestions": gap.improvement_suggestions if gap else [],
        }

    def _build_recommendation_explanation(
        self,
        screening: ScreeningResult,
        gap: SkillGapAnalysis | None,
        job: Job | None,
    ) -> dict[str, Any]:
        rec = screening.recommendation
        score = screening.overall_match_score

        title = ""
        summary = ""
        factors = []
        next_steps = []

        if rec == "strongly_recommend":
            title = "Strongly Recommended"
            summary = f"This candidate is an excellent fit with an overall match score of {score}%. "
            if screening.skill_match_score >= 80:
                summary += "They demonstrate strong skill alignment with the role requirements. "
                factors.append("Excellent skill match")
            if screening.experience_match_score >= 80:
                factors.append("Experience level meets or exceeds requirements")
            if screening.education_match_score >= 80:
                factors.append("Education background is well-aligned")
            next_steps = [
                "Schedule interview promptly — strong candidate",
                "Prepare technical assessment",
                "Consider fast-tracking through pipeline",
            ]
        elif rec == "recommend":
            title = "Recommended"
            summary = f"This candidate is a good fit with an overall match score of {score}%. "
            summary += "They meet most requirements with some minor gaps. "
            if screening.skill_match_score >= 60:
                factors.append("Good skill coverage")
            if screening.experience_match_score >= 60:
                factors.append("Adequate experience level")
            if screening.project_match_score >= 60:
                factors.append("Relevant project experience")
            next_steps = [
                "Schedule standard interview process",
                "Focus on areas where skills are missing",
                "Verify experience claims",
            ]
        elif rec == "consider":
            title = "Consider"
            summary = f"This candidate partially matches with an overall score of {score}%. "
            if screening.missing_required_skills:
                summary += f"Key gaps include: {', '.join(screening.missing_required_skills[:3])}. "
            factors.append("Partial skill match — some gaps exist")
            if screening.experience_match_score < 60:
                factors.append("Experience level may be below requirements")
            next_steps = [
                "Evaluate if gaps can be trained",
                "Consider for alternative roles if available",
                "Assess motivation and learning ability in interview",
            ]
        else:
            title = "Not Recommended"
            summary = f"This candidate has a low match score of {score}% for this role. "
            if screening.missing_required_skills:
                summary += f"Significant skill gaps: {', '.join(screening.missing_required_skills[:3])}. "
            factors.append("Significant gaps in required qualifications")
            next_steps = [
                "Consider for other open positions",
                "Provide feedback if requested",
                "Keep in talent pool for future roles",
            ]

        if screening.strengths:
            factors.extend([f"Strength: {s}" for s in screening.strengths[:2]])
        if screening.weaknesses:
            factors.extend([f"Gap: {w}" for w in screening.weaknesses[:2]])

        return {
            "title": title,
            "summary": summary,
            "factors": factors,
            "next_steps": next_steps,
            "score_breakdown": {
                "skills": screening.skill_match_score,
                "experience": screening.experience_match_score,
                "education": screening.education_match_score,
                "projects": screening.project_match_score,
                "certifications": screening.certification_match_score,
                "location": screening.location_match_score,
                "semantic": screening.semantic_match_score,
            },
        }
