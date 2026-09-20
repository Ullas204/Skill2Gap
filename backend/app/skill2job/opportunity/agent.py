"""Phase 7: Opportunity Unlock — what-if simulation agent.

Deterministic "what if I learn X?" simulation. The candidate states a target
role and/or a list of prospective skills; the agent re-scores the curated
catalog with the shared MatchingEngine using the same inputs plus those
skills. Results are honestly scoped to skill additions the candidate proposed —
nothing is assumed or invented.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.skill2job_models import Skill2JobJob, Skill2JobJobMatch, Skill2JobSimulation
from app.skill2job.matching.schemas import MatchResultEntry
from app.skill2job.opportunity.schemas import (
    OpportunityDashboard,
    OpportunityImpactResponse,
    SimulatedJob,
    SimulationRequest,
    SimulationResult,
    SkillImpact,
    UpliftDetail,
)
from app.skill2job.profile.normalization import canonicalize_skill

logger = logging.getLogger(__name__)

SIMULATION_VERSION = "skill2job-simulation-7.0.0"
IMPACT_VERSION = "skill2job-impact-1.0.0"
UNLOCK_THRESHOLD = 80

# Evidence tiers contribute deterministically to evidence-aware readiness.
# Weakest to strongest, with documented weights; "none" = not recorded anywhere.
EVIDENCE_WEIGHTS = {
    "none": 0.0,
    "claimed": 0.4,
    "supported": 0.6,
    "demonstrated": 0.8,
    "verified": 1.0,
}
EVIDENCE_TIERS = ["none", "claimed", "supported", "demonstrated", "verified"]
UNTESTED_WARNING_FRACTION = 0.30


class OpportunityUnlockAgent:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # ─── Protocol helpers ─────────────────────────────────────────────────

    async def get_results(self, user_id: uuid.UUID) -> dict:
        rows = (
            await self._session.execute(
                select(Skill2JobSimulation)
                .where(Skill2JobSimulation.user_id == user_id)
                .order_by(Skill2JobSimulation.created_at.desc())
                .limit(20)
            )
        ).scalars().all()
        return {
            "items": [
                {
                    "id": str(r.id),
                    "dream_job_title": r.dream_job_title,
                    "skills_added": r.skills_added,
                    "result": r.result,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in rows
            ],
            "total": len(rows),
        }

    # ─── Simulation ───────────────────────────────────────────────────────

    async def simulate(
        self, user_id: uuid.UUID, request: SimulationRequest
    ) -> SimulationResult:
        from app.skill2job.jobs.agent import LocalJobAgent
        from app.skill2job.matching.agent import JobMatchingAgent

        await LocalJobAgent(self._session).ensure_catalog()
        engine = JobMatchingAgent(self._session)
        inputs = await engine._candidate_inputs(user_id, None)
        jobs = (
            await self._session.execute(
                select(Skill2JobJob).where(Skill2JobJob.active.is_(True))
            )
        ).scalars().all()

        baseline_entries = sorted(
            (engine._score_job(j, inputs) for j in jobs),
            key=lambda e: (-e.overall_score, e.job_id),
        )

        added_raw = [s for s in request.skills_to_add if (s or "").strip()]
        added_display: list[str] = []
        simulated_names = list(inputs["skill_names"])
        for raw in added_raw:
            canon = canonicalize_skill(raw)
            if canon["display"].lower() not in {s.lower() for s in simulated_names}:
                simulated_names.append(canon["display"])
                if canon["display"]:
                    added_display.append(canon["display"])

        sim_inputs = {**inputs, "skill_names": simulated_names}
        sim_entries = sorted(
            (engine._score_job(j, sim_inputs) for j in jobs),
            key=lambda e: (-e.overall_score, e.job_id),
        )

        baseline_by_id = {e.job_id: e for e in baseline_entries}

        def to_simulated(e) -> SimulatedJob:
            return SimulatedJob(
                job_id=e.job_id,
                title=e.title,
                company=e.company,
                location=e.location,
                overall_score=e.overall_score,
                recommendation=e.recommendation,
            )

        top_uplift: list[UpliftDetail] = []
        unlocked = 0
        had = {s.lower() for s in inputs["skill_names"]}
        added_pool = [s for s in added_display if s.lower() not in had]
        for entry in sim_entries[: request.limit]:
            before = baseline_by_id.get(entry.job_id)
            if before is None:
                continue
            diff = entry.overall_score - before.overall_score
            if diff <= 0:
                continue
            newly_matched = [
                s
                for s in added_pool
                if s in entry.matched_skills
                and s not in (before.matched_skills or [])
            ][:5]
            became_unlocked = before.overall_score < 80 <= entry.overall_score
            if became_unlocked:
                unlocked += 1
            top_uplift.append(
                UpliftDetail(
                    job_id=entry.job_id,
                    title=entry.title,
                    company=entry.company,
                    before=before.overall_score,
                    after=entry.overall_score,
                    uplift=diff,
                    newly_matched_skills=newly_matched,
                    unlocked=became_unlocked,
                )
            )

        top_uplift.sort(key=lambda d: (-d.uplift, d.job_id))
        notes: list[str] = []
        if not added_display:
            notes.append(
                "Add prospective skills to simulate their impact on your match scores."
            )
        else:
            notes.append(
                f"Simulated learning {len(added_display)} skill(s): {', '.join(added_display[:5])}."
            )
        if unlocked == 0:
            notes.append(
                "No opportunity moved into the strongly-matched band (>80) with these additions."
            )

        result = SimulationResult(
            baseline=[to_simulated(e) for e in baseline_entries[: request.limit]],
            simulated=[to_simulated(e) for e in sim_entries[: request.limit]],
            top_uplift=top_uplift[:5],
            unlocked_count=unlocked,
            target_role=request.dream_job_title,
            skills_added=added_display,
            notes=notes,
            simulation_version=SIMULATION_VERSION,
        )

        self._session.add(
            Skill2JobSimulation(
                user_id=user_id,
                dream_job_title=request.dream_job_title,
                skills_added=added_display,
                result=result.model_dump(mode="json"),
            )
        )
        await self._session.flush()
        return result

    # ─── Dashboard ────────────────────────────────────────────────────────

    async def dashboard(self, user_id: uuid.UUID) -> OpportunityDashboard:
        rows = (
            await self._session.execute(
                select(Skill2JobSimulation)
                .where(Skill2JobSimulation.user_id == user_id)
                .order_by(Skill2JobSimulation.created_at.desc())
            )
        ).scalars().all()
        if not rows:
            return OpportunityDashboard(potential=0, unlocked_count=0, top_roles=[])
        latest = rows[0]
        result = SimulationResult(**latest.result)

        top_uplift = result.top_uplift[0] if result.top_uplift else None
        potential = 0
        for d in result.top_uplift:
            potential = max(potential, d.after)

        roles: dict[str, dict] = {}
        for job in result.simulated:
            role_key = job.title.lower()
            entry = roles.setdefault(role_key, {"role": job.title, "score": 0, "company": job.company})
            if job.overall_score > entry["score"]:
                entry.update(score=job.overall_score, company=job.company)
        top_roles = sorted(roles.values(), key=lambda r: -r["score"])[:5]

        # Phase 3: Populate readiness fields from ReadinessEngine
        readiness_score = 0.0
        readiness_level = "unknown"
        matched_skills_count = 0
        evidence_breakdown: list[dict] = []
        try:
            from app.skill2job.readiness.engine import ReadinessEngine
            readiness_engine = ReadinessEngine(self._session)
            # Use the best-matched job for readiness calculation
            best_job_id = result.top_uplift[0].job_id if result.top_uplift and hasattr(result.top_uplift[0], 'job_id') else None
            if best_job_id:
                readiness = await readiness_engine.calculate(user_id, str(best_job_id))
                readiness_score = readiness.overall_readiness
                matched_skills_count = readiness.matched_count
                evidence_breakdown = [
                    {"skill": e.skill, "level": e.evidence_level, "multiplier": e.evidence_multiplier}
                    for e in readiness.evidence_breakdown[:10]
                ]
                if readiness_score >= 0.8:
                    readiness_level = "strong"
                elif readiness_score >= 0.6:
                    readiness_level = "moderate"
                elif readiness_score >= 0.4:
                    readiness_level = "developing"
                else:
                    readiness_level = "early"
        except Exception:
            pass

        # Calculate potential unlock by skill (top blocking skills)
        potential_unlock_by_skill: list[dict] = []
        if result.top_uplift:
            skill_impact: dict[str, dict] = {}
            for uplift in result.top_uplift:
                for skill in (uplift.newly_matched_skills if hasattr(uplift, 'newly_matched_skills') else []):
                    if skill not in skill_impact:
                        skill_impact[skill] = {"skill": skill, "jobs_affected": 0, "avg_uplift": 0}
                    skill_impact[skill]["jobs_affected"] += 1
                    skill_impact[skill]["avg_uplift"] += uplift.uplift
            for skill, data in skill_impact.items():
                data["avg_uplift"] = round(data["avg_uplift"] / max(data["jobs_affected"], 1), 1)
            potential_unlock_by_skill = sorted(
                skill_impact.values(), key=lambda x: -x["jobs_affected"]
            )[:5]

        # Cost analysis: total cost to learn blocking skills
        cost_analysis: dict = {"total_cost": 0, "currency": "INR", "skills_with_cost": 0}
        try:
            from app.skill2job.learning.resources import _RESOURCE_CATALOG
            for skill_data in potential_unlock_by_skill:
                skill_name = skill_data["skill"]
                for res in _RESOURCE_CATALOG:
                    if skill_name.lower() in [s.lower() for s in res.get("skills", [])]:
                        if res.get("cost") and res["cost"] > 0:
                            cost_analysis["total_cost"] += res["cost"]
                            cost_analysis["skills_with_cost"] += 1
                        break
        except Exception:
            pass

        return OpportunityDashboard(
            top_opportunity=(
                {
                    "title": top_uplift.title,
                    "company": top_uplift.company,
                    "before": top_uplift.before,
                    "after": top_uplift.after,
                    "uplift": top_uplift.uplift,
                }
                if top_uplift
                else None
            ),
            potential=potential,
            unlocked_count=result.unlocked_count,
            top_roles=top_roles,
            readiness=readiness_score,
            readiness_level=readiness_level,
            matched_skills_count=matched_skills_count,
            evidence_breakdown=evidence_breakdown,
            potential_unlock_by_skill=potential_unlock_by_skill,
            cost_analysis=cost_analysis,
        )

    # ─── Per-skill impact (in-memory, never persisted) ─────────────────────

    async def impact(self, user_id: uuid.UUID, limit: int = 10) -> OpportunityImpactResponse:
        """Per-gap opportunity impact analysis (in-memory, never persisted).

        For each skill the candidate is missing in their matched feed we
        re-score exactly those opportunities with the same engine inputs plus
        that ONE skill, then report the grounded delta. No ``Skill2JobSimulation``
        row is ever written and no employment-probability claim is made.
        """
        from app.skill2job.jobs.agent import LocalJobAgent
        from app.skill2job.matching.agent import JobMatchingAgent
        from app.skill2job.training.time_to_ready import (
            TimeToReadyEngine,
            _SKILL_DEPENDENCIES,
        )

        await LocalJobAgent(self._session).ensure_catalog()
        engine = JobMatchingAgent(self._session)

        existing = (
            await self._session.execute(
                select(Skill2JobJobMatch.id)
                .where(Skill2JobJobMatch.user_id == user_id)
                .limit(1)
            )
        ).scalars().first()
        if existing is None:
            await engine.run_match(user_id, job_ids=None, limit=10)

        rows = (
            await self._session.execute(
                select(Skill2JobJobMatch)
                .where(Skill2JobJobMatch.user_id == user_id)
                .order_by(
                    Skill2JobJobMatch.overall_score.desc(),
                    Skill2JobJobMatch.created_at.desc(),
                )
                .limit(max(limit, 1))
            )
        ).scalars().all()
        if not rows:
            return OpportunityImpactResponse(
                total_gaps=0, analysis_jobs=0, version=IMPACT_VERSION
            )

        job_ids = [r.job_id for r in rows]
        jobs = (
            await self._session.execute(
                select(Skill2JobJob).where(Skill2JobJob.id.in_(job_ids))
            )
        ).scalars().all()
        job_map = {j.id: j for j in jobs}

        inputs = await engine._candidate_inputs(user_id, None)
        base_names = list(inputs["skill_names"])

        baseline: dict[str, MatchResultEntry] = {}
        for jid, job in job_map.items():
            baseline[str(jid)] = engine._score_job(job, inputs)

        gap_skills: dict[str, str] = {}
        for r in rows:
            for s in r.missing_required or []:
                gap_skills.setdefault(s.strip().lower(), s.strip())

        all_jobs = (
            await self._session.execute(
                select(Skill2JobJob).where(Skill2JobJob.active.is_(True))
            )
        ).scalars().all()
        demand: dict[str, dict] = {}
        for j in all_jobs:
            for s in j.required_skills or []:
                key = s.strip().lower()
                if not key:
                    continue
                entry = demand.setdefault(key, {"count": 0, "jobs": [], "titles": set()})
                entry["count"] += 1
                entry["jobs"].append(f"{j.title} at {j.company}")
                entry["titles"].add(j.title)

        ttr = TimeToReadyEngine(self._session)
        impacts: list[SkillImpact] = []
        for lower, skill in gap_skills.items():
            sim_inputs = {**inputs, "skill_names": base_names + [skill]}
            sim: dict[str, MatchResultEntry] = {}
            for jid, job in job_map.items():
                sim[str(jid)] = engine._score_job(job, sim_inputs)

            unlock = 0
            improved = 0
            uplifts: list[int] = []
            for jid, entry in sim.items():
                before = baseline[jid].overall_score
                after = entry.overall_score
                if before < UNLOCK_THRESHOLD <= after:
                    unlock += 1
                if after > before:
                    improved += 1
                    uplifts.append(after - before)

            demand_entry = demand.get(lower, {"count": 0, "jobs": [], "titles": set()})
            best = ttr._best_resource_for_skill(skill, free_only=False)
            has_free = ttr._has_free_resource(skill)
            avg_uplift = round(sum(uplifts) / len(uplifts), 1) if uplifts else 0.0
            count = int(demand_entry["count"])
            if unlock > 0:
                priority = "high"
            elif count >= 2 or avg_uplift >= 5:
                priority = "medium"
            else:
                priority = "low"
            impacts.append(
                SkillImpact(
                    skill=skill,
                    demand_count=count,
                    jobs_required=sorted(set(demand_entry["jobs"]))[:20],
                    target_roles=sorted(demand_entry["titles"])[:10],
                    unlock_potential=unlock,
                    improved_jobs=improved,
                    avg_uplift=avg_uplift,
                    effort_hours=best.get("duration_hours") if best else None,
                    has_free_resource=has_free,
                    best_resource_id=best["resource_id"] if best else None,
                    dependencies=list(_SKILL_DEPENDENCIES.get(lower, [])),
                    priority=priority,
                )
            )

        impacts.sort(
            key=lambda s: (-s.unlock_potential, -s.demand_count, -s.avg_uplift, s.skill.lower())
        )
        return OpportunityImpactResponse(
            total_gaps=len(impacts),
            analysis_jobs=len(job_map),
            threshold=UNLOCK_THRESHOLD,
            total_unlock_potential=sum(s.unlock_potential for s in impacts),
            gaps_with_unlock=sum(1 for s in impacts if s.unlock_potential > 0),
            skills=impacts,
            version=IMPACT_VERSION,
        )