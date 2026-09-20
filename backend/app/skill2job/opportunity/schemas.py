"""Phase 7: Opportunity Unlock API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SimulationRequest(BaseModel):
    dream_job_title: str | None = Field(
        default=None, description="The role the candidate is aiming for (free text)."
    )
    own_assessment: str | None = Field(
        default=None, description="Optional self-assessment note (not used for scoring)."
    )
    skills_to_add: list[str] = Field(
        default_factory=list, description="Prospective skills to simulate learning."
    )
    limit: int = Field(default=10, gt=0, le=30)


class SimulatedJob(BaseModel):
    job_id: str
    title: str
    company: str
    location: str | None = None
    overall_score: int
    recommendation: str


class UpliftDetail(BaseModel):
    job_id: str
    title: str
    company: str
    before: int
    after: int
    uplift: int
    newly_matched_skills: list[str] = Field(default_factory=list)
    unlocked: bool = False


class SimulationResult(BaseModel):
    baseline: list[SimulatedJob] = Field(default_factory=list)
    simulated: list[SimulatedJob] = Field(default_factory=list)
    top_uplift: list[UpliftDetail] = Field(default_factory=list)
    unlocked_count: int
    target_role: str | None = None
    skills_added: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    simulation_version: str


class OpportunityDashboard(BaseModel):
    top_opportunity: dict | None = None
    potential: int
    unlocked_count: int
    top_roles: list[dict] = Field(default_factory=list)
    # Phase 3: Readiness fields (populated by ReadinessEngine)
    readiness: float = Field(default=0.0, description="Overall readiness score 0.0-1.0")
    readiness_level: str = Field(default="unknown", description="Readiness level: early, developing, moderate, strong")
    readiness_weighted: bool = False
    readiness_weights: dict[str, float] = Field(default_factory=dict)
    evidence_breakdown: list[dict] = Field(default_factory=list, description="Per-skill evidence assessment")
    matched_skills_count: int = 0
    untested_fraction: float = 0.0
    untested_warning: bool = False
    untested_warning_detail: str | None = None
    readiness_summary: str | None = None
    # Phase 3: Opportunity unlock by skill
    potential_unlock_by_skill: list[dict] = Field(
        default_factory=list,
        description="Top blocking skills that could unlock the most jobs",
    )
    cost_analysis: dict = Field(
        default_factory=dict,
        description="Total cost to learn blocking skills (total_cost, currency, skills_with_cost)",
    )


class SkillImpact(BaseModel):
    skill: str
    demand_count: int = 0
    jobs_required: list[str] = Field(
        default_factory=list, description="Curated jobs listing the skill as required."
    )
    target_roles: list[str] = Field(default_factory=list)
    unlock_potential: int = Field(
        default=0,
        description="Opportunities crossing the strongly-matched band (80) with this one skill.",
    )
    improved_jobs: int = 0
    avg_uplift: float = 0.0
    effort_hours: float | None = Field(
        default=None, description="Best-known course duration; None when unverified."
    )
    has_free_resource: bool = False
    best_resource_id: str | None = None
    dependencies: list[str] = Field(default_factory=list)
    priority: str = "low"


class OpportunityImpactResponse(BaseModel):
    total_gaps: int
    analysis_jobs: int
    threshold: int = 80
    total_unlock_potential: int = 0
    gaps_with_unlock: int = 0
    skills: list[SkillImpact] = Field(default_factory=list)
    version: str = "skill2job-impact-1.0.0"