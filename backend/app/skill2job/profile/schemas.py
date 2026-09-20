"""Profile Agent schemas (Phase 3)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class CompletenessSummary(BaseModel):
    score: int
    total: int
    filled_sections: list[str] = Field(default_factory=list)
    missing_sections: list[str] = Field(default_factory=list)


class NormalizedSkillEntry(BaseModel):
    name: str
    canonical: str | None = None
    category: str | None = None
    known: bool = False
    sources: list[str] = Field(default_factory=list)
    inferred: bool = False


class RecommendationItem(BaseModel):
    category: str  # profile_section | skill_expansion | career
    priority: str  # high | medium | low
    title: str
    description: str


class SkillExpansionSuggestion(BaseModel):
    skill: str
    related_to: list[str] = Field(default_factory=list)
    reason: str


class ProfileDossier(BaseModel):
    user_id: str
    generated_at: datetime
    version: str
    profile: dict[str, Any] = Field(default_factory=dict)
    skills: list[NormalizedSkillEntry] = Field(default_factory=list)
    skill_count: int = 0
    education_count: int = 0
    experience_count: int = 0
    experience_years: float | None = None
    target_roles: list[str] = Field(default_factory=list)
    completeness: CompletenessSummary
    recommendations: list[RecommendationItem] = Field(default_factory=list)
    suggestions: list[SkillExpansionSuggestion] = Field(default_factory=list)
    source_breakdown: dict[str, int] = Field(default_factory=dict)
    corrections_applied: list[dict[str, Any]] = Field(default_factory=list)


class CorrectionItem(BaseModel):
    field: str
    value: str | None = None
    note: str | None = None


class ReviewRequest(BaseModel):
    skills_to_add: list[str] = Field(default_factory=list)
    skills_to_exclude: list[str] = Field(default_factory=list)
    corrections: list[CorrectionItem] = Field(default_factory=list)


class ReviewResult(BaseModel):
    applied_skills: list[dict[str, Any]] = Field(default_factory=list)
    excluded_skills: list[str] = Field(default_factory=list)
    corrections_applied: list[dict[str, Any]] = Field(default_factory=list)