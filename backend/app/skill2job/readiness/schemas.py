"""Schemas for the Evidence-Aware Readiness Engine."""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvidenceStrength(BaseModel):
    """Per-skill evidence assessment."""

    skill: str
    evidence_level: str = Field(
        description="Evidence level: CLAIMED, SUPPORTED, LEARNED, DEMONSTRATED, ASSESSED, VERIFIED"
    )
    evidence_multiplier: float = Field(
        description="Numeric multiplier 0.0-1.0 reflecting evidence strength"
    )
    sources: list[str] = Field(
        default_factory=list,
        description="Data sources supporting this evidence level",
    )
    note: str = Field(default="", description="Human-readable evidence note")


class ReadinessResult(BaseModel):
    """Evidence-aware readiness calculation for a specific job."""

    job_id: str
    job_title: str
    overall_readiness: float = Field(
        description="Overall readiness score 0.0-1.0"
    )
    skill_coverage: float = Field(
        description="Fraction of required skills matched 0.0-1.0"
    )
    evidence_quality: float = Field(
        description="Average evidence quality across matched skills 0.0-1.0"
    )
    critical_gaps: list[str] = Field(
        default_factory=list,
        description="Missing skills with critical/high importance",
    )
    evidence_breakdown: list[EvidenceStrength] = Field(
        default_factory=list,
        description="Per-skill evidence assessment",
    )
    total_required: int = Field(default=0, description="Total required skills count")
    matched_count: int = Field(default=0, description="Number of matched required skills")
    missing_count: int = Field(default=0, description="Number of missing required skills")
    version: str = Field(default="skill2job-readiness-1.0.0")
