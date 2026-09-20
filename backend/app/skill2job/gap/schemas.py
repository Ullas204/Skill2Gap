"""Phase 6 + LLM: Skill Gap Agent API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SkillGapItem(BaseModel):
    skill: str
    role: str
    company: str
    evidence: str
    transferable: list[str] = Field(default_factory=list)
    related_existing: list[str] = Field(default_factory=list)
    gap_kind: str = "skill_gap"
    evidence_note: str | None = None
    priority: str = "high"
    llm_explanation: str | None = None
    llm_learning_advice: str | None = None


class TeachingPlanStep(BaseModel):
    skill: str
    jobs_demanding: list[str] = Field(default_factory=list)
    priority: str = "medium"
    rationale: str
    llm_rationale: str | None = None
    opportunity_impact: str | None = None


class SkillGapAnalysis(BaseModel):
    job_id: str
    job_title: str
    company: str
    overall_score: int
    missing_required_skills: list[str]
    missing_preferred_skills: list[str]
    gap_items: list[SkillGapItem] = Field(default_factory=list)
    experience_gap_description: str | None = None
    education_gap_description: str | None = None
    certification_gap_description: str | None = None
    improvement_suggestions: list[str] = Field(default_factory=list)
    interview_readiness_score: int
    analysis_version: str
    llm_summary: str | None = None
    llm_priority_ranking: list[dict] = Field(default_factory=list)


class SkillGapRequest(BaseModel):
    job_ids: list[str] | None = None
    limit: int = 5


class SkillGapSummary(BaseModel):
    total_analyses: int
    analyzed_jobs: int
    gap_skills: list[dict] = Field(default_factory=list)
    teaching_plan: list[TeachingPlanStep] = Field(default_factory=list)
    llm_overall_assessment: str | None = None