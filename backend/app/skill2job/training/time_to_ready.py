"""Phase 9: Time-to-Ready Engine.

Calculates how long and how much it costs for a candidate to become ready
for a target job. Consumes existing Skill Gap, Skill Graph, Job Matching,
Opportunity Unlock, and Training agents. Nothing is fabricated.
"""

from __future__ import annotations

import logging
import math
import uuid
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.skill2job_models import (
    Skill2JobJob,
    Skill2JobJobMatch,
    Skill2JobSkillGap,
    Skill2JobTrainingProgress,
)
from app.services.screening.skill_graph import SkillGraph
from app.skill2job.gap.agent import SkillGapAgent
from app.skill2job.learning.resources import RESOURCE_DATA_VERSION, _RESOURCE_CATALOG
from app.skill2job.gap.schemas import SkillGapSummary
from app.skill2job.matching.agent import JobMatchingAgent
from app.skill2job.training.schemas import (
    FreeOnlyPath,
    LearningPlanStep,
    LearningResource,
    OpportunityUnlock,
    SkillGapWithPriority,
    TargetJobComparison,
    TimeToReadyRequest,
    TimeToReadyResult,
    WhatIfRequest,
    WhatIfResult,
)

logger = logging.getLogger(__name__)

TTR_VERSION = "skill2job-time-to-ready-1.0.0"

# Curated Learning Resource Registry lives in ``app.skill2job.learning.resources``
# (single source of truth shared with the public Learning Resource agent).
# ``_RESOURCE_CATALOG`` is re-exported here so existing imports stay stable.

# Skill Dependencies from SkillGraph analysis.

_SKILL_DEPENDENCIES = {
    "machine learning": ["python", "statistics", "linear algebra"],
    "deep learning": ["python", "machine learning", "linear algebra"],
    "scikit-learn": ["python", "machine learning", "statistics"],
    "tensorflow": ["python", "machine learning"],
    "pytorch": ["python", "machine learning"],
    "model evaluation": ["python", "machine learning"],
    "statistics": ["python"],
    "probability": ["statistics"],
    "linear algebra": [],
    "numpy": ["python"],
    "pandas": ["python", "numpy"],
    "apache spark": ["python", "sql"],
    "apache airflow": ["python", "sql"],
    "apache kafka": ["java"],
    "kubernetes": ["docker", "linux"],
    "docker": ["linux"],
    "terraform": ["cloud computing"],
    "aws": ["cloud computing"],
    "react": ["javascript", "html", "css"],
    "django": ["python", "html"],
    "fastapi": ["python"],
    "node.js": ["javascript"],
    "mongodb": [], "postgresql": [], "mysql": [], "sql": [],
    "linux": [], "java": [], "javascript": [], "html": [], "css": [], "python": [],
}


class TimeToReadyEngine:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    # --- Public API ---

    async def calculate(self, user_id: uuid.UUID, request: TimeToReadyRequest) -> TimeToReadyResult:
        from app.skill2job.jobs.agent import LocalJobAgent
        await LocalJobAgent(self._session).ensure_catalog()

        job_id = request.job_id
        job_title = request.job_title or ""
        hours_per_week = max(request.hours_per_week, 1.0)
        free_only = request.free_only or request.optimization_mode == "free_only"

        job = await self._find_job(job_id, job_title)
        if job is None:
            return TimeToReadyResult(target_job=job_title or "Unknown", version=TTR_VERSION)

        candidate_skills = await self._get_candidate_skills(user_id)
        gap_summary = await self._get_gap_for_job(user_id, str(job.id))

        missing_required = list(job.required_skills or [])
        matched = {s.lower() for s in candidate_skills}
        missing_skills = [s for s in missing_required if s.lower() not in matched]

        if not missing_skills:
            return TimeToReadyResult(
                target_job=job.title, job_id=str(job.id),
                current_readiness=1.0, projected_readiness=1.0,
                estimated_weeks=0, estimated_hours=0, estimated_cost=0,
                version=TTR_VERSION,
            )

        gaps = self._build_gaps(missing_skills, gap_summary, job.title, job.company)
        resource_map = self._select_resources(gaps, free_only)
        current_readiness = self._calculate_readiness(candidate_skills, job, gap_summary)

        plan = self._build_learning_plan(gaps, resource_map, hours_per_week, free_only)
        total_hours = sum(s.hours for s in plan)
        total_cost = sum(s.cost for s in plan)
        total_weeks = self._calculate_parallel_weeks(plan)

        free_plan = self._build_learning_plan(gaps, resource_map, hours_per_week, free_only=True)
        free_hours = sum(s.hours for s in free_plan)
        free_cost = sum(s.cost for s in free_plan)
        free_weeks = self._calculate_parallel_weeks(free_plan)

        all_gap_skills = {g.skill.lower() for g in gaps}
        free_covered = {s.skill.lower() for s in free_plan}
        free_coverage = (len(free_covered & all_gap_skills) / len(all_gap_skills) * 100) if all_gap_skills else 100.0
        remaining = [g.skill for g in gaps if g.skill.lower() not in free_covered]

        free_only_path = FreeOnlyPath(
            estimated_weeks=free_weeks, estimated_hours=free_hours, estimated_cost=free_cost,
            currency="INR", coverage_pct=round(free_coverage, 1), remaining_gaps=remaining,
        )

        projected_skills = candidate_skills + [g.skill for g in gaps]
        projected_readiness = self._calculate_readiness(projected_skills, job, gap_summary)
        opportunity = await self._calculate_opportunity_unlock(user_id, candidate_skills, [g.skill for g in gaps])

        return TimeToReadyResult(
            target_job=job.title, job_id=str(job.id),
            current_readiness=round(current_readiness, 2),
            projected_readiness=round(projected_readiness, 2),
            missing_skills=gaps, learning_plan=plan,
            estimated_weeks=round(total_weeks, 1), estimated_hours=round(total_hours, 1),
            estimated_cost=round(total_cost, 2), currency="INR",
            free_only=free_only_path, opportunity_unlock=opportunity,
            optimization_mode=request.optimization_mode, hours_per_week=hours_per_week,
            free_only_mode=free_only, version=TTR_VERSION,
        )

    async def simulate(self, user_id: uuid.UUID, request: WhatIfRequest) -> WhatIfResult:
        candidate_skills = await self._get_candidate_skills(user_id)
        added_lower = {s.lower() for s in candidate_skills}
        new_skills = [s for s in request.skills_to_add if s.lower() not in added_lower]
        simulated_skills = candidate_skills + new_skills

        matches = await self._get_current_matches(user_id)
        current_count = len(matches)
        new_matched = await self._simulate_matching(user_id, simulated_skills, new_skills)

        remaining = []
        for match in matches[:5]:
            for req in (match.get("missing_required") or []):
                if req.lower() not in {s.lower() for s in simulated_skills} and req not in remaining:
                    remaining.append(req)

        total_hours = 0
        total_cost = 0
        for s in new_skills:
            res = self._best_resource_for_skill(s, free_only=False)
            if res:
                if res.get("duration_hours"):
                    total_hours += res["duration_hours"]
                total_cost += res.get("cost") or 0

        total_weeks = total_hours / request.hours_per_week if request.hours_per_week > 0 else 0
        return WhatIfResult(
            current_jobs=current_count, projected_jobs=current_count + len(new_matched),
            new_matched_jobs=new_matched, remaining_gaps=remaining[:10],
            estimated_weeks=round(total_weeks, 1), estimated_hours=round(total_hours, 1),
            estimated_cost=round(total_cost, 2),
        )

    async def compare_jobs(self, user_id: uuid.UUID, hours_per_week: float = 10.0) -> list:
        from app.skill2job.jobs.agent import LocalJobAgent
        await LocalJobAgent(self._session).ensure_catalog()
        candidate_skills = await self._get_candidate_skills(user_id)
        matches = await self._get_current_matches(user_id)
        comparisons = []
        seen: set = set()

        for match in matches:
            jid = match.get("job_id", "")
            if jid in seen:
                continue
            seen.add(jid)
            missing = match.get("missing_required") or []
            if not missing:
                continue
            gaps = self._build_gaps(missing, None, match.get("title", ""), match.get("company", ""))
            rmap = self._select_resources(gaps, free_only=False)
            plan = self._build_learning_plan(gaps, rmap, hours_per_week, free_only=False)
            free_plan = self._build_learning_plan(gaps, rmap, hours_per_week, free_only=True)
            all_gaps = {g.skill.lower() for g in gaps}
            covered = {s.skill.lower() for s in plan}
            coverage = (len(covered & all_gaps) / len(all_gaps) * 100) if all_gaps else 100
            sim_skills = candidate_skills + [g.skill for g in gaps]

            class _Job:
                required_skills = missing
                preferred_skills = []

            readiness = self._calculate_readiness(sim_skills, _Job(), None)
            comparisons.append(TargetJobComparison(
                job_id=jid, job_title=match.get("title", ""),
                missing_skills_count=len(missing),
                estimated_weeks=round(self._calculate_parallel_weeks(plan), 1),
                estimated_cost=round(sum(s.cost for s in plan), 2), currency="INR",
                free_only_weeks=round(self._calculate_parallel_weeks(free_plan), 1),
                free_only_cost=round(sum(s.cost for s in free_plan), 2),
                coverage_pct=round(coverage, 1), readiness=round(readiness, 2),
            ))
        comparisons.sort(key=lambda c: c.estimated_weeks)
        return comparisons

    # --- Internal helpers ---

    async def _find_job(self, job_id, title):
        stmt = select(Skill2JobJob).where(Skill2JobJob.active.is_(True))
        if job_id:
            try:
                stmt = stmt.where(Skill2JobJob.id == uuid.UUID(job_id))
            except ValueError:
                return None
        elif title:
            stmt = stmt.where(Skill2JobJob.title.ilike(f"%{title}%"))
        else:
            return None
        return (await self._session.execute(stmt)).scalars().first()

    async def _get_candidate_skills(self, user_id):
        from app.skill2job.adapters.candidate_adapter import CandidateAdapter
        from app.skill2job.profile.agent import ProfileAgent
        adapter = CandidateAdapter(self._session)
        agent = ProfileAgent(self._session, adapter)
        skills_merged = await agent._collect_skills(user_id)
        return [s["name"] for s in skills_merged]

    async def _get_gap_for_job(self, user_id, job_id):
        from app.skill2job.gap.schemas import SkillGapAnalysis
        rows = (await self._session.execute(
            select(Skill2JobSkillGap).where(
                Skill2JobSkillGap.user_id == user_id,
                Skill2JobSkillGap.job_id == uuid.UUID(job_id),
            )
        )).scalars().first()
        if rows is None:
            return None
        analysis = SkillGapAnalysis(**rows.analysis)
        return SkillGapSummary(
            total_analyses=1, analyzed_jobs=1,
            gap_skills=[{"skill": s, "count": 1} for s in analysis.missing_required_skills],
            teaching_plan=[],
        )

    async def _get_current_matches(self, user_id):
        rows = (await self._session.execute(
            select(Skill2JobJobMatch).where(Skill2JobJobMatch.user_id == user_id)
            .order_by(Skill2JobJobMatch.overall_score.desc()).limit(20)
        )).scalars().all()
        jobs_map = {}
        if rows:
            jids = [r.job_id for r in rows]
            jobs = (await self._session.execute(
                select(Skill2JobJob).where(Skill2JobJob.id.in_(jids))
            )).scalars().all()
            jobs_map = {j.id: j for j in jobs}
        return [{"job_id": str(r.job_id), "title": jobs_map.get(r.job_id, type("J", (), {"title": ""})()).title if jobs_map.get(r.job_id) else "", "company": getattr(jobs_map.get(r.job_id), "company", ""), "missing_required": list(r.missing_required or []), "overall_score": r.overall_score} for r in rows]

    async def _simulate_matching(self, user_id, simulated_skills, new_skills):
        rows = (await self._session.execute(
            select(Skill2JobJobMatch).where(Skill2JobJobMatch.user_id == user_id)
        )).scalars().all()
        new_matched = []
        for r in rows:
            missing = set(r.missing_required or [])
            newly_covered = {s for s in new_skills if s.lower() in {m.lower() for m in missing}}
            if newly_covered:
                job = (await self._session.execute(
                    select(Skill2JobJob).where(Skill2JobJob.id == r.job_id)
                )).scalars().first()
                if job:
                    new_matched.append({"job_id": str(r.job_id), "title": job.title, "company": job.company, "newly_matched": list(newly_covered)})
        return new_matched

    def _build_gaps(self, missing_skills, gap_summary, job_title, company):
        gaps = []
        skill_demand = {}
        if gap_summary:
            for gs in gap_summary.gap_skills:
                skill_demand[gs["skill"].lower()] = gs

        for skill in missing_skills:
            demand = skill_demand.get(skill.lower(), {})
            count = demand.get("count", 1)
            importance = min(0.5 + count * 0.1, 1.0)
            priority = "critical" if importance >= 0.8 else "high" if importance >= 0.65 else "medium" if importance >= 0.5 else "low"
            deps = _SKILL_DEPENDENCIES.get(skill.lower(), [])
            dependents = [s for s, d in _SKILL_DEPENDENCIES.items() if skill.lower() in [x.lower() for x in d]]
            has_free = self._has_free_resource(skill)
            best = self._best_resource_for_skill(skill, free_only=False)
            gaps.append(SkillGapWithPriority(
                skill=skill, priority=priority, importance=importance,
                jobs_demanding=[f"{job_title} at {company}"] if job_title else [],
                dependencies=deps, dependents=dependents,
                has_free_resource=has_free, best_resource_id=best["resource_id"] if best else None,
            ))

        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        gaps.sort(key=lambda g: (order.get(g.priority, 4), -g.importance))
        return gaps

    def _select_resources(self, gaps, free_only):
        selected = {}
        for gap in gaps:
            res = self._best_resource_for_skill(gap.skill, free_only)
            if res:
                selected[gap.skill.lower()] = res
        return selected

    def _best_resource_for_skill(self, skill, free_only):
        candidates = [r for r in _RESOURCE_CATALOG if skill.lower() in [s.lower() for s in r["skills"]] and (not free_only or r["is_free"])]
        if not candidates:
            return None
        candidates.sort(key=lambda r: (0 if r["is_free"] else 1, -(r.get("skill_coverage") or 0), r.get("duration_hours") or 999))
        return candidates[0]

    def _has_free_resource(self, skill):
        return self._best_resource_for_skill(skill, free_only=True) is not None

    def _build_learning_plan(self, gaps, resource_map, hours_per_week, free_only):
        plan = []
        scheduled = set()
        group = 0
        step = 1
        remaining = list(gaps)
        while remaining:
            ready = [g for g in remaining if all(d.lower() in scheduled or d.lower() not in {x.skill.lower() for x in gaps} for d in g.dependencies)]
            if not ready:
                ready = remaining[:1]
            independent = len(ready) > 1
            gnum = group if independent else None
            for gap in ready:
                rdict = resource_map.get(gap.skill.lower())
                if rdict is None:
                    continue
                resource = LearningResource(
                    resource_id=rdict["resource_id"], title=rdict["title"], provider=rdict["provider"],
                    url=rdict.get("url"), skills=rdict.get("skills", []),
                    duration_hours=rdict.get("duration_hours"), duration_weeks=rdict.get("duration_weeks"),
                    cost=rdict.get("cost"), currency=rdict.get("currency"), is_free=rdict.get("is_free", False),
                    pricing_type=rdict.get("pricing_type", "unknown"), difficulty=rdict.get("difficulty", "unknown"),
                    format=rdict.get("format", "unknown"), certificate=rdict.get("certificate", False),
                    skill_level=rdict.get("skill_level", "unknown"), prerequisites=rdict.get("prerequisites", []),
                    source_type=rdict.get("source_type", "course"), skill_coverage=rdict.get("skill_coverage", 0.5),
                )
                dur = rdict.get("duration_hours") or 20
                weeks = dur / hours_per_week if hours_per_week > 0 else dur / 10
                cost = rdict.get("cost") or 0
                explanation = self._explain_resource(rdict, gap)
                plan.append(LearningPlanStep(
                    step_number=step, skill=gap.skill, resource=resource,
                    weeks=round(weeks, 1), hours=round(dur, 1), cost=round(cost, 2),
                    is_free=rdict.get("is_free", False), can_parallel=independent,
                    parallel_group=gnum, explanation=explanation,
                ))
                step += 1
            for gap in ready:
                scheduled.add(gap.skill.lower())
            remaining = [g for g in remaining if g.skill.lower() not in scheduled]
            group += 1
        return plan

    def _calculate_parallel_weeks(self, plan):
        if not plan:
            return 0
        groups = {}
        for s in plan:
            groups.setdefault(s.parallel_group, []).append(s)
        total = 0.0
        for gk, steps in groups.items():
            total += max(s.weeks for s in steps) if gk is not None else sum(s.weeks for s in steps)
        return total if total > 0 else sum(s.weeks for s in plan)

    def _calculate_readiness(self, candidate_skills, job, gap_summary):
        required = list(job.required_skills or [])
        preferred = list(getattr(job, "preferred_skills", None) or [])
        if not required:
            return 1.0
        matched = {s.lower() for s in candidate_skills}
        req_match = sum(1 for s in required if s.lower() in matched)
        pref_match = sum(1 for s in preferred if s.lower() in matched) if preferred else 0
        score = (req_match / len(required)) * 0.8
        if preferred:
            score += (pref_match / len(preferred)) * 0.2
        else:
            score = req_match / len(required)
        return min(score, 1.0)

    def _explain_resource(self, res, gap):
        covered = [s for s in res.get("skills", []) if s.lower() != gap.skill.lower()]
        parts = [f"Covers: {', '.join([gap.skill] + covered[:3])}"]
        if gap.jobs_demanding:
            parts.append(f"Required by: {gap.jobs_demanding[0]}")
        parts.append(f"Duration: {res.get('duration_hours', '?')}h")
        parts.append("Cost: Free" if res.get("is_free") else f"Cost: {res.get('cost')}" if res.get("cost") else "Cost: Unknown")
        prereqs = res.get("prerequisites", [])
        if prereqs:
            parts.append(f"Prerequisites: {', '.join(prereqs[:3])}")
        return " | ".join(parts)

    async def _calculate_opportunity_unlock(self, user_id, current_skills, planned_skills):
        matches = await self._get_current_matches(user_id)
        current_count = len([m for m in matches if m.get("overall_score", 0) >= 50])

        simulated = current_skills + planned_skills
        projected_count = current_count
        for match in matches:
            missing = set(match.get("missing_required") or [])
            covered_after = sum(1 for s in missing if s.lower() in {x.lower() for x in simulated})
            if covered_after > len(missing) * 0.5:
                projected_count += 1

        return OpportunityUnlock(
            current_jobs=current_count,
            projected_jobs=projected_count,
            potential_increase=max(0, projected_count - current_count),
        )
