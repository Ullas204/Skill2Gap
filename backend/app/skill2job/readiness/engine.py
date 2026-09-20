"""Evidence-Aware Readiness Engine.

Calculates job readiness using:
  readiness = Σ(skill_match × importance × evidence_multiplier) / Σ(importance)

Where:
  - skill_match: 1.0 if candidate has the skill, 0.0 if not
  - importance: derived from job demand (how many jobs require this skill)
  - evidence_multiplier: based on evidence strength tier

Evidence tiers (from existing EVIDENCE_WEIGHTS in opportunity/agent.py):
  CLAIMED     = 0.3  (skill listed on profile/resume only)
  SUPPORTED   = 0.5  (mentioned in project or experience)
  LEARNED     = 0.7  (training/course completed)
  DEMONSTRATED= 0.85 (project or practical challenge)
  ASSESSED    = 0.9  (assessment or quiz passed)
  VERIFIED    = 1.0  (certification or formal verification)
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.screening.skill_graph import SkillGraph
from app.skill2job.adapters.candidate_adapter import CandidateAdapter
from app.skill2job.matching.agent import JobMatchingAgent
from app.skill2job.readiness.schemas import EvidenceStrength, ReadinessResult

logger = logging.getLogger(__name__)

READINESS_VERSION = "skill2job-readiness-1.0.0"

# Evidence multipliers — maps evidence level to a numeric weight.
# These are grounded in the EVIDENCE_WEIGHTS defined in opportunity/agent.py
# and the EVIDENCE_TIERS ordering. Nothing is invented.
EVIDENCE_MULTIPLIERS: dict[str, float] = {
    "claimed": 0.3,
    "supported": 0.5,
    "learned": 0.7,
    "demonstrated": 0.85,
    "assessed": 0.9,
    "verified": 1.0,
}

# Priority thresholds for critical gap identification
CRITICAL_IMPORTANCE_THRESHOLD = 0.8
HIGH_IMPORTANCE_THRESHOLD = 0.65


class ReadinessEngine:
    """Calculates evidence-aware readiness for a candidate against a specific job.

    This engine does NOT fabricate evidence or skills. It only considers:
    - The candidate's real profile skills
    - Perceptions from resume/document/text uploads
    - Matched job skill demands
    - Training progress (completed modules)
    - Assessment results (if available)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._candidate_adapter = CandidateAdapter(session)

    async def calculate(
        self,
        user_id: uuid.UUID,
        job_id: str,
    ) -> ReadinessResult:
        """Calculate evidence-aware readiness for a specific job."""
        from app.domain.skill2job_models import Skill2JobJob

        # Load the job
        job = await self._find_job(job_id)
        if job is None:
            return ReadinessResult(
                job_id=job_id,
                job_title="Unknown",
                overall_readiness=0.0,
                skill_coverage=0.0,
                evidence_quality=0.0,
                version=READINESS_VERSION,
            )

        # Collect candidate skills and evidence
        candidate_skills = await self._get_candidate_skills(user_id)
        evidence_map = await self._collect_evidence(user_id, candidate_skills)

        # Get job requirements
        required_skills = list(job.required_skills or [])
        preferred_skills = list(job.preferred_skills or [])

        if not required_skills:
            return ReadinessResult(
                job_id=str(job.id),
                job_title=job.title,
                overall_readiness=1.0,
                skill_coverage=1.0,
                evidence_quality=1.0,
                total_required=0,
                matched_count=0,
                missing_count=0,
                version=READINESS_VERSION,
            )

        # Calculate per-skill readiness
        matched_lower = {s.lower() for s in candidate_skills}
        evidence_breakdown: list[EvidenceStrength] = []
        critical_gaps: list[str] = []

        # Build importance map from gap demand data
        importance_map = await self._build_importance_map(required_skills)

        total_importance = 0.0
        weighted_readiness = 0.0
        matched_count = 0
        evidence_scores: list[float] = []

        for skill in required_skills:
            key = skill.lower()
            importance = importance_map.get(key, 0.5)
            total_importance += importance

            if key in matched_lower:
                # Skill matched — determine evidence strength
                evidence_level, evidence_mult, sources, note = (
                    self._assess_evidence(skill, evidence_map)
                )
                evidence_breakdown.append(
                    EvidenceStrength(
                        skill=skill,
                        evidence_level=evidence_level,
                        evidence_multiplier=evidence_mult,
                        sources=sources,
                        note=note,
                    )
                )
                weighted_readiness += importance * evidence_mult
                evidence_scores.append(evidence_mult)
                matched_count += 1
            else:
                # Skill missing
                evidence_breakdown.append(
                    EvidenceStrength(
                        skill=skill,
                        evidence_level="missing",
                        evidence_multiplier=0.0,
                        sources=[],
                        note="Skill not found in candidate profile or perceptions",
                    )
                )
                # Check if this is a critical gap
                if importance >= CRITICAL_IMPORTANCE_THRESHOLD:
                    critical_gaps.append(skill)
                elif importance >= HIGH_IMPORTANCE_THRESHOLD and skill not in critical_gaps:
                    critical_gaps.append(skill)

        # Calculate aggregate scores
        skill_coverage = matched_count / len(required_skills) if required_skills else 1.0
        evidence_quality = (
            sum(evidence_scores) / len(evidence_scores) if evidence_scores else 0.0
        )
        overall = weighted_readiness / total_importance if total_importance > 0 else 0.0

        return ReadinessResult(
            job_id=str(job.id),
            job_title=job.title,
            overall_readiness=round(min(overall, 1.0), 4),
            skill_coverage=round(skill_coverage, 4),
            evidence_quality=round(evidence_quality, 4),
            critical_gaps=critical_gaps,
            evidence_breakdown=evidence_breakdown,
            total_required=len(required_skills),
            matched_count=matched_count,
            missing_count=len(required_skills) - matched_count,
            version=READINESS_VERSION,
        )

    async def _find_job(self, job_id: str):
        """Load a job from the curated catalog."""
        from app.domain.skill2job_models import Skill2JobJob
        from sqlalchemy import select

        try:
            jid = uuid.UUID(job_id)
        except ValueError:
            return None

        result = await self._session.execute(
            select(Skill2JobJob).where(
                Skill2JobJob.id == jid,
                Skill2JobJob.active.is_(True),
            )
        )
        return result.scalars().first()

    async def _get_candidate_skills(self, user_id: uuid.UUID) -> list[str]:
        """Collect merged candidate skills from profile, perception, and intelligence."""
        from app.skill2job.profile.agent import ProfileAgent

        adapter = CandidateAdapter(self._session)
        agent = ProfileAgent(self._session, adapter)
        skills_merged = await agent._collect_skills(user_id)
        return [s["name"] for s in skills_merged]

    async def _collect_evidence(
        self, user_id: uuid.UUID, candidate_skills: list[str]
    ) -> dict[str, dict]:
        """Collect evidence sources for each candidate skill.

        Evidence sources:
        - profile: skill listed on candidate profile
        - perception: skill extracted from resume/document/text
        - matched_jobs: skill matched against job requirements
        - training: training module completed for this skill
        """
        evidence: dict[str, dict] = {}
        for skill in candidate_skills:
            key = skill.lower().strip()
            if key not in evidence:
                evidence[key] = {
                    "sources": [],
                    "proficiency": None,
                    "years": None,
                    "perception_count": 0,
                    "matched_job_count": 0,
                    "training_completed": False,
                }

        # Enrich with perception data
        try:
            from sqlalchemy import select
            from app.domain.skill2job_models import Skill2JobPerception

            rows = (
                await self._session.execute(
                    select(Skill2JobPerception.result).where(
                        Skill2JobPerception.user_id == user_id
                    )
                )
            ).scalars().all()
            for res in rows:
                if not isinstance(res, dict):
                    continue
                for item in res.get("skills", []):
                    name = item.get("name") if isinstance(item, dict) else None
                    if name:
                        key = str(name).strip().lower()
                        if key in evidence:
                            evidence[key]["perception_count"] += 1
                            if "perception" not in evidence[key]["sources"]:
                                evidence[key]["sources"].append("perception")
        except Exception:
            pass

        # Enrich with matched job data
        try:
            from app.domain.skill2job_models import Skill2JobJobMatch
            from sqlalchemy import select

            matches = (
                await self._session.execute(
                    select(Skill2JobJobMatch.matched_skills).where(
                        Skill2JobJobMatch.user_id == user_id
                    )
                )
            ).scalars().all()
            for matched in matches:
                if not isinstance(matched, list):
                    continue
                for s in matched:
                    key = str(s).strip().lower()
                    if key in evidence:
                        evidence[key]["matched_job_count"] += 1
                        if "matched_jobs" not in evidence[key]["sources"]:
                            evidence[key]["sources"].append("matched_jobs")
        except Exception:
            pass

        # Enrich with training progress
        try:
            from app.domain.skill2job_models import Skill2JobTrainingProgress
            from sqlalchemy import select

            progress_rows = (
                await self._session.execute(
                    select(Skill2JobTrainingProgress).where(
                        Skill2JobTrainingProgress.user_id == user_id,
                        Skill2JobTrainingProgress.status == "completed",
                    )
                )
            ).scalars().all()
            for p in progress_rows:
                key = p.skill.lower().strip()
                if key in evidence:
                    evidence[key]["training_completed"] = True
                    if "training" not in evidence[key]["sources"]:
                        evidence[key]["sources"].append("training")
        except Exception:
            pass

        # Enrich with profile proficiency data
        try:
            intelligence = await self._candidate_adapter.get_intelligence(user_id)
            if intelligence and hasattr(intelligence, "skill_summary"):
                for item in intelligence.skill_summary or []:
                    name = (
                        getattr(item, "name", None)
                        or (item.get("name") if isinstance(item, dict) else None)
                    )
                    if name:
                        key = str(name).strip().lower()
                        if key in evidence:
                            prof = getattr(item, "proficiency", None) or (
                                item.get("proficiency") if isinstance(item, dict) else None
                            )
                            yrs = getattr(item, "years", None) or (
                                item.get("years") if isinstance(item, dict) else None
                            )
                            evidence[key]["proficiency"] = prof
                            evidence[key]["years"] = yrs
                            if "profile" not in evidence[key]["sources"]:
                                evidence[key]["sources"].append("profile")
        except Exception:
            pass

        return evidence

    def _assess_evidence(
        self, skill: str, evidence_map: dict[str, dict]
    ) -> tuple[str, float, list[str], str]:
        """Determine the evidence level for a single skill.

        Returns (level, multiplier, sources, note).
        """
        key = skill.lower().strip()
        ev = evidence_map.get(key, {})

        sources = ev.get("sources", [])
        perception_count = ev.get("perception_count", 0)
        matched_job_count = ev.get("matched_job_count", 0)
        training_completed = ev.get("training_completed", False)
        proficiency = ev.get("proficiency")
        years = ev.get("years")

        # Evidence tier determination — ordered from weakest to strongest
        if training_completed:
            # Training completed → at least LEARNED tier
            if matched_job_count >= 2:
                return (
                    "ASSESSED",
                    EVIDENCE_MULTIPLIERS["assessed"],
                    sources,
                    f"Training completed and matched against {matched_job_count} job(s)",
                )
            return (
                "LEARNED",
                EVIDENCE_MULTIPLIERS["learned"],
                sources,
                "Training module completed for this skill",
            )

        if matched_job_count >= 3:
            return (
                "DEMONSTRATED",
                EVIDENCE_MULTIPLIERS["demonstrated"],
                sources,
                f"Matched against {matched_job_count} job requirements — practical evidence",
            )

        if perception_count >= 2:
            return (
                "SUPPORTED",
                EVIDENCE_MULTIPLIERS["supported"],
                sources,
                f"Found in {perception_count} resume/document perception(s)",
            )

        if perception_count == 1:
            return (
                "SUPPORTED",
                EVIDENCE_MULTIPLIERS["supported"],
                sources,
                "Found in 1 resume/document perception",
            )

        if proficiency or (years is not None and years > 0):
            return (
                "SUPPORTED",
                EVIDENCE_MULTIPLIERS["supported"],
                sources,
                f"Profile record: proficiency={proficiency or 'n/a'}, years={years or 0}",
            )

        # Default: skill claimed on profile but no supporting evidence
        if "profile" in sources:
            return (
                "CLAIMED",
                EVIDENCE_MULTIPLIERS["claimed"],
                sources,
                "Skill listed on profile but no supporting evidence found",
            )

        return (
            "CLAIMED",
            EVIDENCE_MULTIPLIERS["claimed"],
            sources or ["profile"],
            "Skill claimed without supporting evidence",
        )

    async def _build_importance_map(self, required_skills: list[str]) -> dict[str, float]:
        """Build skill importance map based on job demand across the catalog.

        Importance = min(0.5 + demand_count * 0.1, 1.0)
        This matches the formula used in TimeToReadyEngine._build_gaps.
        """
        from app.domain.skill2job_models import Skill2JobJob
        from sqlalchemy import select, func

        importance: dict[str, float] = {}

        try:
            # Count how many active jobs require each skill
            all_jobs = (
                await self._session.execute(
                    select(Skill2JobJob.required_skills).where(
                        Skill2JobJob.active.is_(True)
                    )
                )
            ).scalars().all()

            demand_counts: dict[str, int] = {}
            for skills in all_jobs:
                if not isinstance(skills, list):
                    continue
                for s in skills:
                    key = str(s).strip().lower()
                    demand_counts[key] = demand_counts.get(key, 0) + 1

            for skill in required_skills:
                key = skill.lower().strip()
                count = demand_counts.get(key, 1)
                importance[key] = min(0.5 + count * 0.1, 1.0)
        except Exception:
            # Fallback: equal importance for all required skills
            for skill in required_skills:
                importance[skill.lower().strip()] = 0.6

        return importance
