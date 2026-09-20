"""Phase 5: Job Matching Agent.

Deterministic scoring agent that reuses the existing ``MatchingEngine`` and
``SkillGraph``. Every result is persisted per ``(user, job)`` so candidates get
a ranked, explainable feed with zero fabricated intelligence.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.skill2job_models import Skill2JobJob, Skill2JobJobMatch
from app.services.screening.matching_engine import MatchingEngine
from app.services.screening.skill_graph import SkillGraph
from app.skill2job.matching.schemas import (
    JobMatchDetail,
    JobMatchRequest,
    JobMatchResponse,
    MatchResultEntry,
    MatchScores,
    SkillMatchDetail,
)

logger = logging.getLogger(__name__)

MATCH_VERSION = "skill2job-match-5.0.0"

# Interest label -> indicative keywords. Used ONLY to explain why a job was
# surfaced to a candidate (informational). Interests never influence the
# overall score, the recommendation, or any persisted match value, so they
# cannot bias automatic hiring decisions.
_INTEREST_KEYWORDS: dict[str, tuple[str, ...]] = {
    "AI/ML": ("ai", "machine learning", "deep learning", "artificial intelligence", "nlp", "computer vision", "tensorflow", "pytorch"),
    "Data Science": ("data science", "analytics", "data engineer", "pandas", "power bi", "tableau", "statistics"),
    "Web Development": ("web", "frontend", "backend", "full stack", "react", "node", "javascript", "api"),
    "Cloud & DevOps": ("cloud", "aws", "azure", "devops", "kubernetes", "docker", "ci/cd", "terraform"),
    "Cybersecurity": ("security", "cyber", "grc", "penetration", "vulnerability"),
    "UI/UX Design": ("ui", "ux", "user experience", "figma", "design", "wireframe"),
    "Product Management": ("product", "roadmap", "stakeholder", "agile", "backlog"),
    "Mobile Development": ("mobile", "android", "ios", "flutter", "react native"),
    "Database Technologies": ("database", "sql", "nosql", "postgres", "mysql", "oracle"),
    "Testing & QA": ("test", "qa", "quality assurance", "automation", "selenium"),
    "Digital Marketing": ("marketing", "seo", "content", "social media", "campaign"),
    "Fintech & Banking": ("fintech", "banking", "payment", "finance", "financial"),
}


def _interest_hit(interest: str, job_text: str) -> bool:
    """Deterministic, text-level interest-to-job signal (informational only)."""
    needle = interest.strip().lower()
    if not needle:
        return False
    if needle in job_text:
        return True
    for label, keywords in _INTEREST_KEYWORDS.items():
        if label.lower() in needle or needle in label.lower():
            if any(kw in job_text for kw in keywords):
                return True
    return False


class JobMatchingAgent:
    """Score curated opportunities against a candidate profile."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ─── Reason tags (informational, never scored) ───────────────────────

    @staticmethod
    def _build_reasons(
        job: Skill2JobJob,
        interests: list[str],
        matched_skills: list[str],
        location_score: int,
        education_score: int,
        experience_score: int,
    ) -> list[str]:
        reasons: list[str] = []
        if matched_skills:
            reasons.append(f"Skill match — {len(matched_skills)} overlapping skill(s)")
        interests = [i for i in (interests or []) if isinstance(i, str) and i.strip()]
        if interests:
            job_text = " ".join(
                [
                    str(job.title or ""),
                    str(job.company or ""),
                    str(job.location or ""),
                    " ".join(list(job.required_skills or []) + list(job.preferred_skills or [])),
                    str(job.description or ""),
                ]
            ).lower()
            hit = next((i for i in interests if _interest_hit(i, job_text)), None)
            if hit:
                reasons.append(f"Interest match — you've noted interest in {hit.strip()}")
        if location_score > 0:
            reasons.append("Location match — job location fits your preference")
        if education_score > 0 or experience_score > 0:
            reasons.append("Education/experience relevant to this role")
        if not reasons:
            reasons.append("Broad fit based on your overall profile")
        return reasons

    # ─── Protocol helpers ─────────────────────────────────────────────────

    async def match_candidate_profile(self, state: dict) -> list[dict]:
        match = await self.run_match(
            user_id=state.get("user_id"),
            location=state.get("location"),
            limit=state.get("limit"),
        )
        return [m.model_dump(mode="json") for m in match]

    async def get_results(self, user_id: uuid.UUID, limit: int = 20) -> list[dict]:
        rows = (
            await self._session.execute(
                select(Skill2JobJobMatch)
                .where(Skill2JobJobMatch.user_id == user_id)
                .order_by(Skill2JobJobMatch.overall_score.desc(), Skill2JobJobMatch.created_at.desc())
                .limit(min(limit, 50))
            )
        ).scalars().all()
        job_ids = [r.job_id for r in rows]
        jobs: dict[uuid.UUID, Skill2JobJob] = {}
        if job_ids:
            found = (
                await self._session.execute(
                    select(Skill2JobJob).where(Skill2JobJob.id.in_(job_ids))
                )
            ).scalars().all()
            jobs = {j.id: j for j in found}
        out = []
        interests: list[str] = []
        try:
            from app.skill2job.adapters.candidate_adapter import CandidateAdapter

            interests = await CandidateAdapter(self._session).get_interests(user_id)
        except Exception:
            interests = []
        for r in rows:
            job = jobs.get(r.job_id)
            reasons = self._build_reasons(
                job,
                interests,
                list(r.matched_skills or []),
                r.location_score,
                r.education_score,
                r.experience_score,
            ) if job else []
            out.append(
                JobMatchResponse(
                    job_id=str(r.job_id),
                    title=job.title if job else "",
                    company=job.company if job else "",
                    location=job.location if job else None,
                    remote_type=job.remote_type if job else None,
                    overall_score=r.overall_score,
                    recommendation=r.recommendation,
                    strength_level=r.strength_level,
                    matched_skills=list(r.matched_skills or []),
                    missing_required=list(r.missing_required or []),
                    suggested_skills=list(r.suggested_skills or []),
                    reasons=reasons,
                ).model_dump(mode="json")
            )
        return out

    # ─── Scoring ──────────────────────────────────────────────────────────

    async def _candidate_inputs(self, user_id: uuid.UUID, location_override: str | None):
        from app.skill2job.adapters.candidate_adapter import CandidateAdapter
        from app.skill2job.profile.agent import ProfileAgent

        adapter = CandidateAdapter(self._session)
        profile = await adapter.get_profile(user_id)
        try:
            intelligence = await adapter.get_intelligence(user_id)
        except Exception:
            intelligence = None

        agent = ProfileAgent(self._session, adapter)
        skills_merged = await agent._collect_skills(user_id)
        skill_names = [s["name"] for s in skills_merged]

        years = intelligence.total_experience_years if intelligence else 0.0
        degrees = []
        if intelligence and intelligence.highest_qualification:
            degrees.append(str(intelligence.highest_qualification))
        project_count = intelligence.project_count if intelligence else 0
        cert_count = intelligence.certification_count if intelligence else 0
        location = location_override or (profile.location or "") if profile else None

        snippet_parts = []
        if profile:
            for part in (profile.current_role, profile.bio):
                if part:
                    snippet_parts.append(str(part))
        snippet_parts.extend(skill_names[:15])
        snippet = " ".join(snippet_parts)

        return {
            "skill_names": skill_names,
            "years": float(years or 0.0),
            "degrees": degrees,
            "project_count": project_count or 0,
            "cert_count": cert_count or 0,
            "location": location,
            "snippet": snippet,
            "interests": list(profile.interests or []) if profile else [],
        }

    def _score_job(self, job: Skill2JobJob, inputs: dict) -> MatchResultEntry:
        skill_score, matched, missing_required, missing_preferred, transferable, similarity_map = (
            MatchingEngine.calculate_skill_match_enhanced(
                inputs["skill_names"],
                list(job.required_skills or []),
                list(job.preferred_skills or []),
            )
        )
        experience_score = MatchingEngine.calculate_experience_match(
            inputs["years"], job.experience_required
        )
        education_score = MatchingEngine.calculate_education_match(
            inputs["degrees"], job.education_required
        )
        project_score = MatchingEngine.calculate_project_match(
            inputs["project_count"], [], list(job.required_skills or [])
        )
        certification_score = MatchingEngine.calculate_certification_match([], None)
        location_score = MatchingEngine.calculate_location_match(
            inputs["location"], job.location or ""
        )
        employment_type_score = MatchingEngine.calculate_employment_type_match(
            None, job.employment_type or "Full-time"
        )
        semantic_score = MatchingEngine.calculate_semantic_similarity(
            job.description, inputs["snippet"]
        )
        overall = MatchingEngine.calculate_overall_score(
            skill_score,
            experience_score,
            education_score,
            project_score,
            certification_score,
            location_score,
            employment_type_score,
            semantic_score,
        )
        recommendation = MatchingEngine.determine_recommendation(overall)
        strength_level = MatchingEngine.determine_strength_level(overall)

        suggested: list[str] = []
        for req in missing_required:
            suggested.append(req)
            related = SkillGraph.get_related_skills(req)
            for r in related:
                if r.lower() not in {s.lower() for s in inputs["skill_names"]}:
                    suggested.append(r)
                    break
        for t in transferable:
            suggested.append(t)

        reasons = self._build_reasons(
            job,
            inputs.get("interests", []),
            matched,
            location_score,
            education_score,
            experience_score,
        )

        return MatchResultEntry(
            job_id=str(job.id),
            title=job.title,
            company=job.company,
            location=job.location,
            remote_type=job.remote_type,
            overall_score=overall,
            scores=MatchScores(
                skill=skill_score,
                experience=experience_score,
                education=education_score,
                project=project_score,
                certification=certification_score,
                location=location_score,
                employment_type=employment_type_score,
                semantic=semantic_score,
            ),
            recommendation=recommendation,
            strength_level=strength_level,
            matched_skills=matched,
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            transferable_skills=transferable,
            suggested_skills=suggested,
            match_version=MATCH_VERSION,
            reasons=reasons,
        )

    async def run_match(
        self,
        user_id: uuid.UUID,
        job_ids: list[str] | None = None,
        location: str | None = None,
        limit: int | None = None,
    ) -> list[MatchResultEntry]:
        from app.skill2job.jobs.agent import LocalJobAgent

        await LocalJobAgent(self._session).ensure_catalog()
        stmt = select(Skill2JobJob).where(Skill2JobJob.active.is_(True))
        if job_ids:
            uuids = []
            for jid in job_ids:
                try:
                    uuids.append(uuid.UUID(jid))
                except ValueError:
                    continue
            if not uuids:
                return []
            stmt = stmt.where(Skill2JobJob.id.in_(uuids))
        jobs = (await self._session.execute(stmt)).scalars().all()

        inputs = await self._candidate_inputs(user_id, location)
        scored = [self._score_job(j, inputs) for j in jobs]
        scored.sort(key=lambda e: (-e.overall_score, e.job_id))

        surfaced = scored[:limit] if limit else scored
        for entry in surfaced:
            values = {
                "user_id": user_id,
                "job_id": uuid.UUID(entry.job_id),
                "overall_score": entry.overall_score,
                "skill_score": entry.scores.skill,
                "experience_score": entry.scores.experience,
                "education_score": entry.scores.education,
                "project_score": entry.scores.project,
                "certification_score": entry.scores.certification,
                "location_score": entry.scores.location,
                "employment_type_score": entry.scores.employment_type,
                "semantic_score": entry.scores.semantic,
                "matched_skills": entry.matched_skills,
                "missing_required": entry.missing_required,
                "missing_preferred": entry.missing_preferred,
                "transferable_skills": entry.transferable_skills,
                "suggested_skills": entry.suggested_skills,
                "recommendation": entry.recommendation,
                "strength_level": entry.strength_level,
                "match_version": MATCH_VERSION,
            }
            stmt = sqlite_insert(Skill2JobJobMatch).values(**values)
            stmt = stmt.on_conflict_do_update(
                index_elements=[Skill2JobJobMatch.user_id, Skill2JobJobMatch.job_id],
                set_={
                    "overall_score": stmt.excluded.overall_score,
                    "skill_score": stmt.excluded.skill_score,
                    "experience_score": stmt.excluded.experience_score,
                    "education_score": stmt.excluded.education_score,
                    "project_score": stmt.excluded.project_score,
                    "certification_score": stmt.excluded.certification_score,
                    "location_score": stmt.excluded.location_score,
                    "employment_type_score": stmt.excluded.employment_type_score,
                    "semantic_score": stmt.excluded.semantic_score,
                    "matched_skills": stmt.excluded.matched_skills,
                    "missing_required": stmt.excluded.missing_required,
                    "missing_preferred": stmt.excluded.missing_preferred,
                    "transferable_skills": stmt.excluded.transferable_skills,
                    "suggested_skills": stmt.excluded.suggested_skills,
                    "recommendation": stmt.excluded.recommendation,
                    "strength_level": stmt.excluded.strength_level,
                    "match_version": stmt.excluded.match_version,
                },
            )
            await self._session.execute(stmt)
        await self._session.flush()
        logger.info("matched %d opportunities for user=%s", len(surfaced), user_id)
        return surfaced

    # ─── Match categories (reproducible, documented) ─────────────────────
    #
    # Category is derived deterministically from the persisted/deterministic
    # match values so the same profile + catalog always yields the same label.
    #  - UNKNOWN  : no candidate skills captured yet
    #  - MATCHED  : zero missing required skills and overall >= 65
    #  - PARTIAL  : some missing required skill, but at least one required
    #               matched OR overall >= 45
    #  - MISSING  : zero required skills matched and overall < 45

    @staticmethod
    def determine_category(
        overall_score: int,
        missing_required: list[str],
        matched_required: int,
        has_profile_skills: bool,
    ) -> str:
        if not has_profile_skills:
            return "unknown"
        if not missing_required and overall_score >= 65:
            return "matched"
        if missing_required and (matched_required > 0 or overall_score >= 45):
            return "partial"
        return "missing"

    _CATEGORY_DESCRIPTIONS: dict[str, str] = {
        "unknown": "No candidate skills captured yet — score cannot be meaningfully categorized.",
        "matched": "All required skills are covered and the overall score is strong.",
        "partial": "Some required skills are missing; the role is achievable with targeted growth.",
        "missing": "Required skills are largely uncovered and the overall score is weak.",
    }

    async def get_match_detail(
        self, user_id: uuid.UUID, job_id: str
    ) -> JobMatchDetail | None:
        """Build a single, explainable per-job match detail (deterministic)."""
        from app.skill2job.adapters.candidate_adapter import CandidateAdapter
        from app.skill2job.jobs.agent import LocalJobAgent

        await LocalJobAgent(self._session).ensure_catalog()
        try:
            job_uuid = uuid.UUID(job_id)
        except ValueError:
            return None
        job = (
            await self._session.execute(
                select(Skill2JobJob).where(
                    Skill2JobJob.id == job_uuid,
                    Skill2JobJob.active.is_(True),
                )
            )
        ).scalar_one_or_none()
        if job is None:
            return None
        return await self._build_match_detail(user_id, job)

    async def _build_match_detail(
        self, user_id: uuid.UUID, job: Skill2JobJob
    ) -> JobMatchDetail:
        from app.skill2job.adapters.candidate_adapter import CandidateAdapter

        inputs = await self._candidate_inputs(user_id, None)
        evidence_map = await CandidateAdapter(self._session).get_skill_evidence_map(
            user_id
        )

        required = list(job.required_skills or [])
        preferred = list(job.preferred_skills or [])
        skill_score, matched, missing_required, missing_preferred, transferable, sim_map = (
            MatchingEngine.calculate_skill_match_enhanced(
                inputs["skill_names"], required, preferred
            )
        )
        experience_score = MatchingEngine.calculate_experience_match(
            inputs["years"], job.experience_required
        )
        education_score = MatchingEngine.calculate_education_match(
            inputs["degrees"], job.education_required
        )
        project_score = MatchingEngine.calculate_project_match(
            inputs["project_count"], [], required
        )
        certification_score = MatchingEngine.calculate_certification_match([], None)
        location_score = MatchingEngine.calculate_location_match(
            inputs["location"], job.location or ""
        )
        employment_type_score = MatchingEngine.calculate_employment_type_match(
            None, job.employment_type or "Full-time"
        )
        semantic_score = MatchingEngine.calculate_semantic_similarity(
            job.description, inputs["snippet"]
        )
        overall = MatchingEngine.calculate_overall_score(
            skill_score,
            experience_score,
            education_score,
            project_score,
            certification_score,
            location_score,
            employment_type_score,
            semantic_score,
        )
        recommendation = MatchingEngine.determine_recommendation(overall)
        strength_level = MatchingEngine.determine_strength_level(overall)

        matched_required_set: set[str] = set(required) & set(matched)
        category = self.determine_category(
            overall,
            missing_required,
            len(matched_required_set),
            bool(inputs["skill_names"]),
        )

        skill_details: list[SkillMatchDetail] = []
        for skill in required + preferred:
            kind = "required" if skill in required else "preferred"
            status = "missing"
            if skill in matched:
                status = "matched"
            elif skill in transferable:
                status = "transferable"
            ev = evidence_map.get(skill.strip().lower())
            if status == "missing":
                evidence_state = "none"
                notes = "Not found in your profile or perception history."
                if ev:
                    notes = (
                        "Related skill is present but the exact requirement was not matched. "
                        + "; ".join(ev["notes"])
                    )
            elif ev:
                evidence_state = ev["state"]
                notes = "; ".join(ev["notes"]) or "Matched by the skill engine."
                if status == "transferable":
                    notes += " Nearest skill counted as transferable coverage."
            else:
                evidence_state = "claimed"
                notes = "Recorded as matched by the skill engine."
                for syn in SkillGraph.SYNONYMS.get(skill.strip().lower(), []):
                    if evidence_map.get(syn):
                        evidence_state = evidence_map[syn]["state"]
                        notes = (
                            f"Matched via synonym '{syn}'. "
                            + "; ".join(evidence_map[syn]["notes"])
                        )
                        break
            skill_details.append(
                SkillMatchDetail(
                    skill=skill,
                    kind=kind,
                    status=status,
                    evidence_state=evidence_state,
                    similarity=sim_map.get(skill),
                    evidence_notes=notes,
                )
            )

        explanation = self._build_explanation(
            inputs["skill_names"],
            required,
            matched,
            missing_required,
            transferable,
            skill_score,
            experience_score,
            education_score,
            project_score,
            certification_score,
            location_score,
            employment_type_score,
            semantic_score,
            overall,
            recommendation,
            category,
        )
        reasons = self._build_reasons(
            job,
            inputs.get("interests", []),
            matched,
            location_score,
            education_score,
            experience_score,
        )

        suggested: list[str] = []
        for req in missing_required:
            suggested.append(req)
            related = SkillGraph.get_related_skills(req)
            for r in related:
                if r.lower() not in {s.lower() for s in inputs["skill_names"]}:
                    suggested.append(r)
                    break
        for t in transferable:
            suggested.append(t)

        return JobMatchDetail(
            job_id=str(job.id),
            title=job.title,
            company=job.company,
            location=job.location,
            remote_type=job.remote_type,
            overall_score=overall,
            category=category,
            categories_explained=self._CATEGORY_DESCRIPTIONS.get(category, ""),
            scores=MatchScores(
                skill=skill_score,
                experience=experience_score,
                education=education_score,
                project=project_score,
                certification=certification_score,
                location=location_score,
                employment_type=employment_type_score,
                semantic=semantic_score,
            ),
            skill_details=skill_details,
            explanation=explanation,
            reasons=reasons,
            recommendation=recommendation,
            strength_level=strength_level,
            matched_skills=matched,
            missing_required=missing_required,
            missing_preferred=missing_preferred,
            transferable_skills=transferable,
            suggested_skills=suggested,
            match_version=MATCH_VERSION,
        )

    @staticmethod
    def _build_explanation(
        skill_names: list[str],
        required: list[str],
        matched: list[str],
        missing_required: list[str],
        transferable: list[str],
        skill_score: int,
        experience_score: int,
        education_score: int,
        project_score: int,
        certification_score: int,
        location_score: int,
        employment_type_score: int,
        semantic_score: int,
        overall: int,
        recommendation: str,
        category: str,
    ) -> list[str]:
        parts: list[str] = []
        parts.append(
            f"Your semantic matching profile (n={len(skill_names)}) was scored "
            f"against {len(required)} required + {len(matched)} overlapping skill(s)."
        )
        parts.append(
            "Component scores: skills %s, experience %s, education %s, projects %s, "
            "certifications %s, location %s, employment type %s, semantic text %s (all /100)."
            % (
                skill_score,
                experience_score,
                education_score,
                project_score,
                certification_score,
                location_score,
                employment_type_score,
                semantic_score,
            )
        )
        if missing_required:
            parts.append(
                f"{len(missing_required)} required skill(s) uncovered: "
                + ", ".join(missing_required[:5])
            )
        if transferable:
            parts.append(
                "Transferable coverage via the skill graph: "
                + ", ".join(transferable[:5])
            )
        parts.append(
            f"Overall {overall}/100 → '{recommendation}' band, category '{category}' "
            f"(weighted default, match version {MATCH_VERSION})."
        )
        return parts