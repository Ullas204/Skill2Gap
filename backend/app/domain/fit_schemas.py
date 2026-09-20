"""Response schemas for evidence-grounded job fit intelligence (Phase 2)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

MatchStatus = Literal["match", "partial", "gap", "unknown"]
EvidenceStrength = Literal["strong", "moderate", "weak", "none"]
RequirementLevel = Literal["required", "preferred"]
RequirementType = Literal["skill", "experience", "education", "certification", "responsibility"]


class EvidenceItem(BaseModel):
    """A verifiable quote from the candidate's resume supporting a conclusion."""

    source: Literal[
        "experience", "project", "certification", "education",
        "skills_section", "resume_text",
    ]
    quote: str = Field(min_length=1)
    context: str | None = None
    section: str | None = None


class RequirementResult(BaseModel):
    requirement: str
    requirement_type: RequirementType
    level: RequirementLevel
    category: str | None = None
    status: MatchStatus
    evidence_strength: EvidenceStrength
    reason: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class ExperienceAlignment(BaseModel):
    status: MatchStatus
    required_years: float | None = None
    relevant_years: float | None = None
    total_years: float | None = None
    relevance_basis: Literal["relevant_experience", "total_experience", "none"] = "none"
    reason: str


class ResponsibilityAlignment(BaseModel):
    responsibility: str
    alignment: EvidenceStrength
    evidence: list[EvidenceItem] = Field(default_factory=list)


class SkillGapSummary(BaseModel):
    strengths: list[str] = Field(default_factory=list)
    partial: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    unknown: list[str] = Field(default_factory=list)


class ScoreBreakdown(BaseModel):
    """Transparent overall-fit score components (weights visible in code)."""

    weights: dict[str, float]
    components: dict[str, float | None]
    formula: str


class OverallFit(BaseModel):
    classification: Literal[
        "strong_match", "good_match", "partial_match", "low_match",
        "insufficient_evidence",
    ]
    score: int = Field(ge=0, le=100)
    breakdown: ScoreBreakdown
    summary: str
    summary_source: Literal["deterministic", "llm_polished"]
    disclaimer: str = (
        "AI-assisted fit assessment based on resume evidence. "
        "This is decision support, not a hiring decision."
    )


class JobRequirementsInfo(BaseModel):
    extracted_count: int
    extractor_version: str


class FitResponse(BaseModel):
    job_id: str
    job_title: str
    candidate_id: str
    candidate_name: str
    resume_id: str | None = None
    requirements: list[RequirementResult] = Field(default_factory=list)
    experience_alignment: ExperienceAlignment
    responsibilities: list[ResponsibilityAlignment] = Field(default_factory=list)
    skill_gaps: SkillGapSummary
    overall: OverallFit
    requirements_info: JobRequirementsInfo
    cached: bool = False
    engine_version: str
