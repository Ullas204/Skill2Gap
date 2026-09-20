"""Phase 9: Learning Resource Intelligence API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.skill2job.training.schemas import LearningResource


class LearningResourcePublic(LearningResource):
    """Public learning resource view. Extends the existing resource schema
    with auditable verification metadata (derived, never fabricated)."""

    verified: bool = False
    description: str | None = None


class SkillResourceCandidate(BaseModel):
    """A deterministic mapping between one skill and one curated resource."""

    resource: LearningResourcePublic
    mapping_kind: Literal["exact", "synonym", "fallback"] = "exact"
    coverage_pct: float = Field(default=0.0, ge=0.0, le=100.0)
    rationale: str = ""


class ResourceMappingResponse(BaseModel):
    """Deterministic skill → resource mapping for a single skill."""

    skill: str
    mapped: bool
    resources: list[SkillResourceCandidate] = Field(default_factory=list)
    version: str = "skill2job-resource-data-1.0.0"


class ResourceListResponse(BaseModel):
    """Catalog listing with verification metadata and a data-integrity note."""

    total: int
    resources: list[LearningResourcePublic] = Field(default_factory=list)
    version: str = "skill2job-resource-data-1.0.0"