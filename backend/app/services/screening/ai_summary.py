from __future__ import annotations

import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

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
    ScreeningResult,
    Skill,
    SkillGapAnalysis,
    User,
)
from app.repositories.candidate.profile import CandidateProfileRepository
from app.repositories.candidate.resume import ParsedResumeDataRepository, ResumeRepository
from app.repositories.jobs.job import JobApplicationRepository, JobRepository
from app.repositories.screening.screening import (
    CandidateRankingRepository,
    ScreeningResultRepository,
    SkillGapAnalysisRepository,
)
from app.services.screening.skill_graph import SkillGraph

logger = logging.getLogger(__name__)


class AISummaryService:
    """Generate AI-powered candidate summaries and intelligence reports."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.screening_repo = ScreeningResultRepository(session)
        self.ranking_repo = CandidateRankingRepository(session)
        self.skill_gap_repo = SkillGapAnalysisRepository(session)
        self.profile_repo = CandidateProfileRepository(session)
        self.resume_repo = ResumeRepository(session)
        self.parsed_repo = ParsedResumeDataRepository(session)
        self.job_repo = JobRepository(session)
        self.app_repo = JobApplicationRepository(session)

    async def generate_candidate_summary(
        self,
        candidate_id: uuid.UUID,
        job_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        profile = await self.profile_repo.get_by_user_id(candidate_id)
        user = await self.session.get(User, candidate_id)
        if not profile or not user:
            return {"error": "Candidate not found"}

        candidate_skills = await self._get_skill_names(profile)
        experiences = await self._get_experiences(profile)
        degrees = await self._get_degrees(profile)
        certifications = await self._get_certifications(profile)
        projects = await self._get_projects(profile)
        total_experience = self._calc_total_experience(experiences)

        professional_summary = self._build_professional_summary(
            user.full_name, profile, total_experience, candidate_skills, degrees,
        )
        top_skills = self._rank_top_skills(candidate_skills, experiences, projects)
        strengths = self._identify_profile_strengths(
            total_experience, candidate_skills, degrees, certifications, projects, profile,
        )
        weaknesses = self._identify_profile_weaknesses(
            total_experience, candidate_skills, degrees, profile,
        )
        career_highlights = self._extract_career_highlights(experiences, projects)
        risk_factors = self._assess_risk_factors(profile, total_experience, experiences)
        experience_level = self._classify_experience_level(total_experience)
        technical_expertise = self._assess_technical_expertise(candidate_skills, projects, experiences)
        leadership_potential = self._assess_leadership_potential(experiences, profile)
        learning_ability = self._assess_learning_ability(candidate_skills, certifications, profile)

        result: dict[str, Any] = {
            "candidate_id": str(candidate_id),
            "candidate_name": user.full_name,
            "candidate_email": user.email,
            "professional_summary": professional_summary,
            "top_skills": top_skills,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "career_highlights": career_highlights,
            "risk_factors": risk_factors,
            "experience_level": experience_level,
            "technical_expertise": technical_expertise,
            "leadership_potential": leadership_potential,
            "learning_ability": learning_ability,
            "total_experience_years": total_experience,
            "education_summary": degrees,
            "certification_count": len(certifications),
            "project_count": len(projects),
        }

        if job_id:
            screening = await self.screening_repo.get_by_job_and_candidate(job_id, candidate_id)
            if screening:
                gap = await self.skill_gap_repo.get_by_screening_result(screening.id)
                result["job_match_score"] = screening.overall_match_score
                result["hiring_recommendation"] = screening.recommendation
                result["matched_skills"] = screening.matched_skills
                result["missing_skills"] = screening.missing_required_skills
                result["strengths_from_screening"] = screening.strengths
                result["weaknesses_from_screening"] = screening.weaknesses
                if gap:
                    result["interview_readiness"] = gap.interview_readiness_score
                    result["improvement_suggestions"] = gap.improvement_suggestions

        return result

    async def generate_job_summary(self, job_id: uuid.UUID) -> dict[str, Any]:
        job = await self.session.get(Job, job_id)
        if not job:
            return {"error": "Job not found"}

        applications = await self.app_repo.list_by_job(job_id)
        screenings = await self.screening_repo.list_by_job(job_id)
        rankings = await self.ranking_repo.list_by_job(job_id)

        total_applicants = len(applications)
        total_screened = len(screenings)

        if not screenings:
            return {
                "job_id": str(job_id),
                "job_title": job.title,
                "total_applicants": total_applicants,
                "total_screened": 0,
                "average_score": 0,
                "top_candidates": [],
                "score_distribution": {},
                "recommendation_breakdown": {},
            }

        scores = [s.overall_match_score for s in screenings]
        avg_score = sum(scores) / len(scores) if scores else 0

        score_dist = {"excellent": 0, "good": 0, "average": 0, "low": 0}
        for s in scores:
            if s >= 80:
                score_dist["excellent"] += 1
            elif s >= 65:
                score_dist["good"] += 1
            elif s >= 45:
                score_dist["average"] += 1
            else:
                score_dist["low"] += 1

        rec_dist: dict[str, int] = {}
        for s in screenings:
            rec = s.recommendation
            rec_dist[rec] = rec_dist.get(rec, 0) + 1

        all_matched_skills: dict[str, int] = {}
        all_missing_skills: dict[str, int] = {}
        for s in screenings:
            for skill in (s.matched_skills or []):
                all_matched_skills[skill] = all_matched_skills.get(skill, 0) + 1
            for skill in (s.missing_required_skills or []):
                all_missing_skills[skill] = all_missing_skills.get(skill, 0) + 1

        top_matched = sorted(all_matched_skills.items(), key=lambda x: -x[1])[:10]
        top_missing = sorted(all_missing_skills.items(), key=lambda x: -x[1])[:10]

        top_candidates = []
        for ranking in rankings[:5]:
            user = await self.session.get(User, ranking.candidate_id)
            screening = await self.screening_repo.get_by_job_and_candidate(
                job_id, ranking.candidate_id,
            )
            top_candidates.append({
                "candidate_id": str(ranking.candidate_id),
                "candidate_name": user.full_name if user else "",
                "rank": ranking.rank,
                "score": ranking.overall_score,
                "strength_level": ranking.strength_level,
                "recommendation": screening.recommendation if screening else "consider",
            })

        return {
            "job_id": str(job_id),
            "job_title": job.title,
            "total_applicants": total_applicants,
            "total_screened": total_screened,
            "average_score": round(avg_score, 1),
            "top_candidates": top_candidates,
            "score_distribution": score_dist,
            "recommendation_breakdown": rec_dist,
            "most_common_matched_skills": [{"skill": s, "count": c} for s, c in top_matched],
            "most_common_missing_skills": [{"skill": s, "count": c} for s, c in top_missing],
        }

    async def generate_recruiter_dashboard(self, recruiter_id: uuid.UUID) -> dict[str, Any]:
        jobs = await self.job_repo.list_by_recruiter(recruiter_id)
        total_jobs = len(jobs)
        total_applications = 0
        total_screened = 0
        all_scores: list[int] = []

        job_summaries = []
        for job in jobs:
            apps = await self.app_repo.list_by_job(job.id)
            screenings = await self.screening_repo.list_by_job(job.id)
            app_count = len(apps)
            screened_count = len(screenings)
            total_applications += app_count
            total_screened += screened_count
            scores = [s.overall_match_score for s in screenings]
            all_scores.extend(scores)
            avg = sum(scores) / len(scores) if scores else 0

            top_ranked = await self.ranking_repo.list_by_job(job.id)
            top_name = ""
            top_score = 0
            if top_ranked:
                top_user = await self.session.get(User, top_ranked[0].candidate_id)
                top_name = top_user.full_name if top_user else ""
                top_score = top_ranked[0].overall_score

            job_summaries.append({
                "job_id": str(job.id),
                "job_title": job.title,
                "applicant_count": app_count,
                "screened_count": screened_count,
                "average_score": round(avg, 1),
                "top_candidate_name": top_name,
                "top_candidate_score": top_score,
                "status": job.status.value if hasattr(job.status, "value") else str(job.status),
            })

        overall_avg = sum(all_scores) / len(all_scores) if all_scores else 0
        recent_rankings = []
        for job in jobs[:3]:
            rankings = await self.ranking_repo.list_by_job(job.id)
            for r in rankings[:2]:
                user = await self.session.get(User, r.candidate_id)
                recent_rankings.append({
                    "job_title": job.title,
                    "candidate_name": user.full_name if user else "",
                    "score": r.overall_score,
                    "rank": r.rank,
                    "rank_change": r.rank_change,
                })

        return {
            "total_jobs": total_jobs,
            "total_applications": total_applications,
            "total_screened": total_screened,
            "average_score": round(overall_avg, 1),
            "job_summaries": job_summaries,
            "recent_rankings": recent_rankings[:10],
        }

    # ─── Private helpers ──────────────────────────────────────────────

    async def _get_skill_names(self, profile: CandidateProfile) -> list[str]:
        from sqlalchemy import select as sa_select
        stmt = (
            sa_select(Skill.name)
            .join(CandidateSkill, CandidateSkill.skill_id == Skill.id)
            .where(CandidateSkill.profile_id == profile.id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _get_experiences(self, profile: CandidateProfile) -> list[dict]:
        from sqlalchemy import select
        stmt = select(Experience).where(Experience.profile_id == profile.id)
        result = await self.session.execute(stmt)
        exps = result.scalars().all()
        return [
            {
                "company": e.company,
                "title": e.job_title,
                "technologies": e.technologies or "",
                "responsibilities": e.responsibilities or "",
                "start_date": str(e.start_date) if e.start_date else "",
                "end_date": str(e.end_date) if e.end_date else "",
                "is_current": e.is_current,
            }
            for e in exps
        ]

    async def _get_degrees(self, profile: CandidateProfile) -> list[str]:
        from sqlalchemy import select
        stmt = select(Education.degree).where(Education.profile_id == profile.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _get_certifications(self, profile: CandidateProfile) -> list[str]:
        from sqlalchemy import select
        stmt = select(Certification.name).where(Certification.profile_id == profile.id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def _get_projects(self, profile: CandidateProfile) -> list[dict]:
        from sqlalchemy import select
        stmt = select(Project).where(Project.profile_id == profile.id)
        result = await self.session.execute(stmt)
        projects = result.scalars().all()
        return [
            {
                "title": p.title,
                "description": p.description or "",
                "technologies": p.technologies or "",
            }
            for p in projects
        ]

    @staticmethod
    def _calc_total_experience(experiences: list[dict]) -> float:
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

    @staticmethod
    def _build_professional_summary(
        name: str,
        profile: CandidateProfile,
        total_exp: float,
        skills: list[str],
        degrees: list[str],
    ) -> str:
        parts = []
        role = profile.current_role or "professional"
        location = f" based in {profile.location}" if profile.location else ""
        parts.append(f"{name} is a {role}{location} with {total_exp:.1f} years of experience.")
        if degrees:
            parts.append(f"Holds {degrees[0]} degree.")
        if skills:
            top = skills[:5]
            parts.append(f"Skilled in {', '.join(top)}.")
        if profile.bio:
            parts.append(profile.bio[:200])
        return " ".join(parts)

    @staticmethod
    def _rank_top_skills(
        skills: list[str], experiences: list[dict], projects: list[dict],
    ) -> list[dict]:
        skill_freq: dict[str, int] = {}
        for s in skills:
            skill_freq[s] = skill_freq.get(s, 0) + 1
        for exp in experiences:
            techs = exp.get("technologies", "")
            for t in [t.strip() for t in techs.split(",") if t.strip()]:
                norm = SkillGraph.find_canonical(t) or t.lower()
                for sk in skills:
                    if SkillGraph.are_synonyms(sk, t) or sk.lower() == norm:
                        skill_freq[sk] = skill_freq.get(sk, 0) + 3
        for proj in projects:
            techs = proj.get("technologies", "")
            for t in [t.strip() for t in techs.split(",") if t.strip()]:
                for sk in skills:
                    if SkillGraph.are_synonyms(sk, t) or sk.lower() == t.lower():
                        skill_freq[sk] = skill_freq.get(sk, 0) + 2
        ranked = sorted(skill_freq.items(), key=lambda x: -x[1])
        return [{"skill": s, "relevance": min(c * 15, 100)} for s, c in ranked[:10]]

    @staticmethod
    def _identify_profile_strengths(
        total_exp: float,
        skills: list[str],
        degrees: list[str],
        certs: list[str],
        projects: list[dict],
        profile: CandidateProfile,
    ) -> list[str]:
        strengths = []
        if total_exp >= 5:
            strengths.append(f"Strong experience with {total_exp:.1f}+ years in the field")
        elif total_exp >= 2:
            strengths.append(f"Solid experience with {total_exp:.1f} years of professional work")
        if len(skills) >= 8:
            strengths.append(f"Diverse technical skillset ({len(skills)} skills)")
        elif len(skills) >= 4:
            strengths.append(f"Good technical foundation ({len(skills)} skills)")
        if len(certs) >= 2:
            strengths.append(f"Multiple certifications ({len(certs)} total)")
        elif len(certs) == 1:
            strengths.append("Has relevant certification")
        if len(projects) >= 3:
            strengths.append(f"Strong project portfolio ({len(projects)} projects)")
        if profile.linkedin_url:
            strengths.append("Active professional online presence")
        if profile.github_url:
            strengths.append("Open source / code portfolio available")
        if not strengths:
            strengths.append("Profile shows potential for growth")
        return strengths

    @staticmethod
    def _identify_profile_weaknesses(
        total_exp: float,
        skills: list[str],
        degrees: list[str],
        profile: CandidateProfile,
    ) -> list[str]:
        weaknesses = []
        if total_exp < 1:
            weaknesses.append("Limited professional experience")
        elif total_exp < 3:
            weaknesses.append("Early career professional — may need mentorship")
        if len(skills) < 3:
            weaknesses.append("Limited skill set recorded — consider adding more skills")
        if not degrees:
            weaknesses.append("No formal education recorded")
        if not profile.bio:
            weaknesses.append("No professional bio — adding one improves profile visibility")
        if not profile.linkedin_url and not profile.github_url:
            weaknesses.append("No professional links provided")
        if not weaknesses:
            weaknesses.append("Minor gaps in profile completeness")
        return weaknesses

    @staticmethod
    def _extract_career_highlights(
        experiences: list[dict], projects: list[dict],
    ) -> list[str]:
        highlights = []
        for exp in experiences[:3]:
            title = exp.get("title", "")
            company = exp.get("company", "")
            if title and company:
                highlights.append(f"{title} at {company}")
        for proj in projects[:2]:
            title = proj.get("title", "")
            if title:
                highlights.append(f"Project: {title}")
        if not highlights:
            highlights.append("Building professional experience")
        return highlights

    @staticmethod
    def _assess_risk_factors(
        profile: CandidateProfile, total_exp: float, experiences: list[dict],
    ) -> list[str]:
        risks = []
        if total_exp == 0:
            risks.append("No work experience recorded")
        if len(experiences) == 0:
            risks.append("Employment history not documented")
        if total_exp > 0 and len(experiences) == 1:
            risks.append("Limited job history — single employer")
        if total_exp > 10 and profile.current_role is None:
            risks.append("Senior professional without current role specified")
        if not risks:
            risks.append("No significant risk factors identified")
        return risks

    @staticmethod
    def _classify_experience_level(total_exp: float) -> str:
        if total_exp >= 10:
            return "Senior / Lead"
        if total_exp >= 5:
            return "Mid-Senior"
        if total_exp >= 3:
            return "Mid-Level"
        if total_exp >= 1:
            return "Junior"
        return "Entry Level / Fresher"

    @staticmethod
    def _assess_technical_expertise(
        skills: list[str], projects: list[dict], experiences: list[dict],
    ) -> str:
        score = len(skills) * 5
        score += len(projects) * 10
        tech_in_exp = 0
        for exp in experiences:
            techs = exp.get("technologies", "")
            if techs:
                tech_in_exp += len([t for t in techs.split(",") if t.strip()])
        score += tech_in_exp * 3
        if score >= 80:
            return "Expert"
        if score >= 50:
            return "Advanced"
        if score >= 25:
            return "Intermediate"
        return "Beginner"

    @staticmethod
    def _assess_leadership_potential(experiences: list[dict], profile: CandidateProfile) -> str:
        leadership_signals = 0
        for exp in experiences:
            title = (exp.get("title", "") or "").lower()
            if any(kw in title for kw in ["lead", "senior", "manager", "director", "head", "principal", "staff"]):
                leadership_signals += 2
            resp = (exp.get("responsibilities", "") or "").lower()
            if any(kw in resp for kw in ["lead", "managed", "mentored", "supervised", "coordinated"]):
                leadership_signals += 1
        if profile.current_role and any(kw in profile.current_role.lower() for kw in ["lead", "senior", "manager"]):
            leadership_signals += 2
        if leadership_signals >= 4:
            return "High"
        if leadership_signals >= 2:
            return "Moderate"
        return "Developing"

    @staticmethod
    def _assess_learning_ability(
        skills: list[str], certs: list[str], profile: CandidateProfile,
    ) -> str:
        score = 0
        score += min(len(skills) * 2, 20)
        score += min(len(certs) * 10, 30)
        if profile.bio and len(profile.bio) > 100:
            score += 5
        if score >= 40:
            return "High"
        if score >= 20:
            return "Moderate"
        return "Developing"
