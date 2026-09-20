"""Local Job Intelligence (Phase 4)."""

from app.skill2job.jobs.agent import LocalJobAgent
from app.skill2job.jobs.ingestion import ensure_seeded

__all__ = ["LocalJobAgent", "ensure_seeded"]