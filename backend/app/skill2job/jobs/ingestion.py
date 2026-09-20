"""Curated job catalog ingestion (Phase 4).

Loads the deterministic local-market dataset into ``skill2job_jobs``. The
loader is idempotent: rows are upserted by ``(source, external_id)``. Seeding
never touches the recruiter-facing ``jobs`` table.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.skill2job_models import Skill2JobJob

logger = logging.getLogger(__name__)

DATASET_PATH = Path(__file__).resolve().parent.parent / "data" / "curated_jobs.json"
DATASET_VERSION = "skill2job-curated-jobs-v1"


async def ensure_seeded(session: AsyncSession) -> dict:
    """Upsert the curated dataset. Returns {loaded, updated, total}."""
    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        payload = json.load(f)
    jobs = payload.get("jobs", [])

    loaded = 0
    updated = 0
    for item in jobs:
        ext = item.get("external_id")
        source = item.get("source", "curated")
        existing = (
            await session.execute(
                select(Skill2JobJob).where(
                    Skill2JobJob.source == source,
                    Skill2JobJob.external_id == ext,
                )
            )
        ).scalars().first()
        fields = {
            "title": item["title"],
            "company": item["company"],
            "location": item.get("location"),
            "remote_type": item.get("remote_type"),
            "employment_type": item.get("employment_type"),
            "experience_required": item.get("experience_required"),
            "education_required": item.get("education_required"),
            "description": item.get("description", ""),
            "required_skills": item.get("required_skills") or [],
            "preferred_skills": item.get("preferred_skills") or [],
            "salary_range": item.get("salary_range"),
            "salary_min": item.get("salary_min"),
            "salary_max": item.get("salary_max"),
            "currency": item.get("currency", "USD"),
            "source": item.get("source", "curated"),
            "source_url": item.get("source_url"),
            "external_id": ext,
            "posted_at": datetime.now(timezone.utc),
            "expires_at": item.get("expires_at"),
            "active": item.get("active", True),
            "ai_summary": item.get("ai_summary"),
        }
        if existing is None:
            session.add(Skill2JobJob(**fields))
            await session.flush()
            loaded += 1
        else:
            needs_update = any(
                getattr(existing, key) != value
                for key, value in fields.items()
                if hasattr(existing, key)
            )
            if needs_update:
                for key, value in fields.items():
                    if hasattr(existing, key):
                        setattr(existing, key, value)
                await session.flush()
                updated += 1
    total = (
        await session.execute(
            select(Skill2JobJob).where(Skill2JobJob.source == "curated")
        )
    ).scalars().all()
    return {
        "dataset": DATASET_VERSION,
        "loaded": loaded,
        "updated": updated,
        "total": len(total),
    }