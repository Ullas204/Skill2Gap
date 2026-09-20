"""Phase 8-9: Training Agent and Time-to-Ready API schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class TrainingModule(BaseModel):
    module_key: str
    skill: str
    title: str
    provider: str
    url: str | None = None
    resource_type: str
    source_status: Literal["verified", "unverified"] = "unverified"
    duration_hours: float | None = None
    duration_weeks: float | None = None
    cost: float | None = None
    currency: str | None = None
    is_free: bool = False
    pricing_type: Literal["free", "paid", "subscription", "one_time", "unknown"] = "unknown"
    difficulty: Literal["beginner", "intermediate", "advanced", "unknown"] = "unknown"
    prerequisites: list[str] = Field(default_factory=list)
    skill_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    last_verified_at: str | None = None
    llm_recommendation_reason: str | None = None
    llm_opportunity_impact: str | None = None


class TrainingPlan(BaseModel):
    modules: list[TrainingModule] = Field(default_factory=list)
    total_modules: int = 0
    version: str
    llm_plan_summary: str | None = None


class ModuleProgressRequest(BaseModel):
    module_key: str
    status: str = Field(default="completed", pattern=r"^(in_progress|completed)$")


# -- Time-to-Ready Schemas (Phase 9) --


class LearningResource(BaseModel):
    resource_id: str
    title: str
    provider: str
    url: str | None = None
    skills: list[str] = Field(default_factory=list)
    duration_hours: float | None = None
    duration_weeks: float | None = None
    cost: float | None = None
    currency: str | None = None
    is_free: bool = False
    pricing_type: Literal["free", "paid", "subscription", "one_time", "unknown"] = "unknown"
    difficulty: Literal["beginner", "intermediate", "advanced", "unknown"] = "unknown"
    format: Literal["self_paced", "instructor_led", "hybrid", "unknown"] = "unknown"
    certificate: bool = False
    skill_level: Literal["beginner", "intermediate", "advanced", "unknown"] = "unknown"
    prerequisites: list[str] = Field(default_factory=list)
    source_type: str = "course"
    skill_coverage: float = Field(default=0.5, ge=0.0, le=1.0)
    last_verified_at: str | None = None


class SkillGapWithPriority(BaseModel):
    skill: str
    priority: str = "medium"
    importance: float = 0.5
    jobs_demanding: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    dependents: list[str] = Field(default_factory=list)
    has_free_resource: bool = False
    best_resource_id: str | None = None


class LearningPlanStep(BaseModel):
    step_number: int
    skill: str
    resource: LearningResource
    weeks: float
    hours: float
    cost: float
    is_free: bool
    can_parallel: bool = False
    parallel_group: int | None = None
    explanation: str = ""


class TimeToReadyRequest(BaseModel):
    job_id: str | None = None
    job_title: str | None = None
    hours_per_week: float = Field(default=10.0, gt=0, le=60)
    free_only: bool = False
    optimization_mode: Literal["fastest", "cheapest", "free_only", "balanced"] = "balanced"


class FreeOnlyPath(BaseModel):
    estimated_weeks: float = 0.0
    estimated_hours: float = 0.0
    estimated_cost: float = 0.0
    currency: str = "INR"
    coverage_pct: float = 0.0
    remaining_gaps: list[str] = Field(default_factory=list)


class OpportunityUnlock(BaseModel):
    current_jobs: int = 0
    projected_jobs: int = 0
    potential_increase: int = 0


class TimeToReadyResult(BaseModel):
    target_job: str
    job_id: str | None = None
    current_readiness: float = 0.0
    projected_readiness: float = 0.0
    missing_skills: list[SkillGapWithPriority] = Field(default_factory=list)
    learning_plan: list[LearningPlanStep] = Field(default_factory=list)
    estimated_weeks: float = 0.0
    estimated_hours: float = 0.0
    estimated_cost: float = 0.0
    currency: str = "INR"
    free_only: FreeOnlyPath = Field(default_factory=FreeOnlyPath)
    opportunity_unlock: OpportunityUnlock = Field(default_factory=OpportunityUnlock)
    optimization_mode: str = "balanced"
    hours_per_week: float = 10.0
    free_only_mode: bool = False
    version: str = "skill2job-time-to-ready-1.0.0"


class WhatIfRequest(BaseModel):
    skills_to_add: list[str] = Field(default_factory=list)
    hours_per_week: float = Field(default=10.0, gt=0, le=60)


class WhatIfResult(BaseModel):
    current_jobs: int = 0
    projected_jobs: int = 0
    new_matched_jobs: list[dict] = Field(default_factory=list)
    remaining_gaps: list[str] = Field(default_factory=list)
    estimated_weeks: float = 0.0
    estimated_hours: float = 0.0
    estimated_cost: float = 0.0


class TargetJobComparison(BaseModel):
    job_id: str
    job_title: str
    missing_skills_count: int
    estimated_weeks: float
    estimated_cost: float
    currency: str = "INR"
    free_only_weeks: float
    free_only_cost: float
    coverage_pct: float
    readiness: float
