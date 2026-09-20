"""Phase 4: Local Job Intelligence agent.

The local job agent operates over the deterministic curated catalog stored in
``skill2job_jobs`` (seeded idempotently from ``data/curated_jobs.json``). It
keeps candidate-visible jobs fully separate from recruiter job postings.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.skill2job_models import Skill2JobJob
from app.skill2job.jobs.ingestion import DATASET_VERSION, ensure_seeded
from app.skill2job.jobs.schemas import (
    CuratedJobCounts,
    CuratedJobFilters,
    CuratedJobPage,
    SkillDemandItem,
    SkillDemandResponse,
)

logger = logging.getLogger(__name__)

_PAGE_SIZE_DEFAULT = 20
_PAGE_SIZE_MAX = 50

_SUPPORTED_REMOTE = {"remote", "hybrid", "on-site"}

# Role keywords used for candidate-aware browsing when a profile is available.
_ROLE_SCAN_TERMS = [
    "backend",
    "frontend",
    "full stack",
    "fullstack",
    "data",
    "machine learning",
    "ml",
    "devops",
    "sre",
    "cloud",
    "mobile",
    "android",
    "ios",
    "qa",
    "test",
    "security",
    "product",
    "architect",
    "database",
    "scala",
    "rust",
    "java",
    "python",
    "react",
    "node",
]

_LOCATION_CANON = {
    "bengaluru": "Bengaluru",
    "bangalore": "Bengaluru",
    "hyderabad": "Hyderabad",
    "pune": "Pune",
    "chennai": "Chennai",
    "gurugram": "Gurugram",
    "gurgaon": "Gurugram",
    "noida": "Noida",
    "remote": None,
}


def _to_job_dict(job: Skill2JobJob) -> dict:
    return {
        "id": str(job.id),
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "remote_type": job.remote_type,
        "employment_type": job.employment_type,
        "experience_required": job.experience_required,
        "education_required": job.education_required,
        "description": job.description,
        "required_skills": job.required_skills or [],
        "preferred_skills": job.preferred_skills or [],
        "salary_range": job.salary_range,
        "salary_min": job.salary_min,
        "salary_max": job.salary_max,
        "currency": job.currency,
        "source": job.source,
        "source_url": job.source_url,
        "external_id": job.external_id,
        "posted_at": job.posted_at.isoformat() if job.posted_at else None,
    }


def _matches_location(job: Skill2JobJob, location: str | None) -> float:
    """0 = no match, 1 = exact, 0.5 = remote-friendly."""
    if not location or location.lower() in ("remote", ""):
        return 0.5 if job.remote_type == "remote" else 0.0
    canon = _LOCATION_CANON.get(location.lower(), location.title())
    if canon and job.location and job.location.lower() == canon.lower():
        return 1.0
    if job.remote_type == "remote":
        return 0.5
    return 0.0


def _role_score(job: Skill2JobJob, profile) -> float:
    """Keyword overlap between the profile targets and the job title."""
    if profile is None:
        return 0.5
    targets: list[str] = []
    if getattr(profile, "current_role", None):
        targets.append(str(profile.current_role))
    for entry in getattr(profile, "target_roles", []) or []:
        if isinstance(entry, dict):
            targets.append(str(entry.get("role", "")))
        else:
            targets.append(str(entry))
    haystack = (job.title or "").lower()
    score = 0.0
    for target in targets:
        tl = target.lower()
        for term in _ROLE_SCAN_TERMS:
            if term in tl and term in haystack:
                score = max(score, 1.0)
                break
        for token in tl.replace("/", " ").replace(",", " ").split():
            if len(token) > 3 and token in haystack:
                score = max(score, 0.8)
                break
    return score


class LocalJobAgent:
    """Provide candidate-facing job intelligence from the curated catalog."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def ensure_catalog(self) -> dict:
        return await ensure_seeded(self.session)

    async def list_jobs(self, filters: CuratedJobFilters) -> CuratedJobPage:
        await self.ensure_catalog()
        stmt = select(Skill2JobJob).where(Skill2JobJob.active.is_(True))
        if filters.location:
            canon = _LOCATION_CANON.get(filters.location.lower())
            if canon:
                stmt = stmt.where(Skill2JobJob.location == canon)
        if filters.remote_only:
            stmt = stmt.where(Skill2JobJob.remote_type.isnot(None))
            stmt = stmt.where(
                Skill2JobJob.remote_type.in_(["remote", "hybrid"])
            )
        if filters.keyword:
            kw = f"%{filters.keyword.lower()}%"
            stmt = stmt.where(
                (Skill2JobJob.title.ilike(kw))
                | (Skill2JobJob.company.ilike(kw))
                | (Skill2JobJob.description.ilike(kw))
            )
        if filters.role_keyword:
            rk = f"%{filters.role_keyword.lower()}%"
            stmt = stmt.where(Skill2JobJob.title.ilike(rk))

        total_rows = (await self.session.execute(stmt)).scalars().all()
        total = len(total_rows)
        page = total_rows[
            filters.offset : filters.offset + min(filters.limit or _PAGE_SIZE_DEFAULT, _PAGE_SIZE_MAX)
        ]
        return CuratedJobPage(
            total=total,
            offset=filters.offset,
            limit=filters.limit or _PAGE_SIZE_DEFAULT,
            jobs=[_to_job_dict(j) for j in page],
        )

    async def job_counts(self) -> CuratedJobCounts:
        await self.ensure_catalog()
        rows = (
            await self.session.execute(
                select(Skill2JobJob).where(Skill2JobJob.active.is_(True))
            )
        ).scalars().all()
        by_location: dict[str, int] = {}
        remote = 0
        for j in rows:
            if j.remote_type in ("remote", "hybrid"):
                remote += 1
            loc = j.location or "Remote"
            by_location[loc] = by_location.get(loc, 0) + 1
        top_locations = sorted(by_location.items(), key=lambda kv: (-kv[1], kv[0]))[:8]
        return CuratedJobCounts(
            total=len(rows),
            remote=remote,
            on_site=len(rows) - remote,
            top_locations=[{"location": k, "count": v} for k, v in top_locations],
            dataset=DATASET_VERSION,
        )

    async def fetch_jobs(self, profile=None, location: str | None = None) -> list[dict]:
        """Candidate-aware fetch of the most relevant curated jobs (max 10)."""
        await self.ensure_catalog()
        rows = (
            await self.session.execute(
                select(Skill2JobJob).where(Skill2JobJob.active.is_(True))
            )
        ).scalars().all()
        scored = []
        for j in rows:
            loc_score = _matches_location(j, location)
            role_score = _role_score(j, profile)
            combined = role_score * max(0.2, loc_score) if loc_score > 0 else role_score * 0.25
            scored.append((combined, role_score, loc_score, j))
        scored.sort(key=lambda pair: (-pair[0], -pair[1], -pair[2], pair[3].title.lower()))
        return [_to_job_dict(j) for _, _, _, j in scored[:10]]

    async def get_job(self, job_id: str) -> dict | None:
        """Return a single active curated job by id, or None."""
        await self.ensure_catalog()
        try:
            job_id_uuid = uuid.UUID(job_id)
        except ValueError:
            return None
        row = (
            await self.session.execute(
                select(Skill2JobJob).where(
                    Skill2JobJob.id == job_id_uuid,
                    Skill2JobJob.active.is_(True),
                )
            )
        ).scalar_one_or_none()
        return _to_job_dict(row) if row else None

    async def skill_demand(self) -> SkillDemandResponse:
        """Dataset-wide skill demand aggregated over the active curated catalog.

        Demand is derived purely from the persisted curated jobs (required and
        preferred skill lists) — never invented. Thresholds are documented here:
        high = demanded by >= 5 jobs, medium = 2-4, low = 1.
        """
        await self.ensure_catalog()
        rows = (
            await self.session.execute(
                select(Skill2JobJob).where(Skill2JobJob.active.is_(True))
            )
        ).scalars().all()

        required: dict[str, int] = {}
        preferred: dict[str, int] = {}
        titles: dict[str, list[str]] = {}
        for j in rows:
            for s in j.required_skills or []:
                key = s.strip().lower()
                if not key:
                    continue
                required[key] = required.get(key, 0) + 1
                titles.setdefault(key, []).append(f"{j.title} at {j.company}")
            for s in j.preferred_skills or []:
                key = s.strip().lower()
                if not key:
                    continue
                preferred[key] = preferred.get(key, 0) + 1
                titles.setdefault(key, []).append(f"{j.title} at {j.company}")

        items: list[SkillDemandItem] = []
        for key in sorted(set(required) | set(preferred)):
            req = required.get(key, 0)
            pref = preferred.get(key, 0)
            total = req + pref
            if total >= 5:
                level = "high"
            elif total >= 2:
                level = "medium"
            else:
                level = "low"
            label = key.title()
            items.append(
                SkillDemandItem(
                    skill=label,
                    required_count=req,
                    preferred_count=pref,
                    count=total,
                    jobs_demanding=sorted(set(titles.get(key, []))),
                    demand_level=level,
                )
            )
        items.sort(key=lambda it: (-it.count, it.skill.lower()))
        return SkillDemandResponse(
            dataset=DATASET_VERSION,
            total_jobs=len(rows),
            items=items,
        )