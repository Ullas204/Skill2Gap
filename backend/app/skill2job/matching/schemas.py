"""Phase 5: Job Matching Agent API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class JobMatchRequest(BaseModel):
    job_ids: list[str] | None = Field(
        default=None, description="Optional curated job ids to score. Defaults to the active catalog."
    )
    location: str | None = Field(
        default=None, description="Override candidate location used for location scoring."
    )
    limit: int | None = Field(default=None, gt=0, le=50)


class MatchScores(BaseModel):
    skill: int
    experience: int
    education: int
    project: int
    certification: int
    location: int
    employment_type: int
    semantic: int


class MatchResultEntry(BaseModel):
    job_id: str
    title: str
    company: str
    location: str | None = None
    remote_type: str | None = None
    overall_score: int
    scores: MatchScores
    recommendation: str
    strength_level: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    missing_preferred: list[str] = Field(default_factory=list)
    transferable_skills: list[str] = Field(default_factory=list)
    suggested_skills: list[str] = Field(default_factory=list)
    match_version: str
    reasons: list[str] = Field(default_factory=list)


class JobMatchResponse(BaseModel):
    job_id: str
    title: str
    company: str
    location: str | None = None
    remote_type: str | None = None
    overall_score: int
    recommendation: str
    strength_level: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    suggested_skills: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)


class SkillMatchDetail(BaseModel):
    skill: str
    kind: str = "required"
    status: str = "missing"
    evidence_state: str = "none"
    similarity: float | None = None
    evidence_notes: str = ""


class JobMatchDetail(BaseModel):
    job_id: str
    title: str
    company: str
    location: str | None = None
    remote_type: str | None = None
    overall_score: int
    category: str = "unknown"
    categories_explained: str = ""
    scores: MatchScores
    skill_details: list[SkillMatchDetail] = Field(default_factory=list)
    explanation: list[str] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    recommendation: str
    strength_level: str
    matched_skills: list[str] = Field(default_factory=list)
    missing_required: list[str] = Field(default_factory=list)
    missing_preferred: list[str] = Field(default_factory=list)
    transferable_skills: list[str] = Field(default_factory=list)
    suggested_skills: list[str] = Field(default_factory=list)
    match_version: str