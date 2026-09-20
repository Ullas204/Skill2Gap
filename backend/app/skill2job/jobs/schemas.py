"""Local job intelligence API schemas (Phase 4)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class CuratedJobResponse(BaseModel):
    id: str
    title: str
    company: str
    location: str | None = None
    remote_type: str | None = None
    employment_type: str | None = None
    experience_required: str | None = None
    education_required: str | None = None
    description: str
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    salary_range: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str = "USD"
    source: str = "curated"
    source_url: str | None = None
    external_id: str | None = None
    posted_at: str | None = None


class CuratedJobFilters(BaseModel):
    location: str | None = None
    remote_only: bool = False
    keyword: str | None = None
    role_keyword: str | None = None
    limit: int | None = Field(default=None, gt=0, le=60)
    offset: int = Field(default=0, ge=0)


class CuratedJobPage(BaseModel):
    total: int
    offset: int = 0
    limit: int = 20
    jobs: list[CuratedJobResponse] = Field(default_factory=list)


class LocationCount(BaseModel):
    location: str
    count: int


class CuratedJobCounts(BaseModel):
    total: int
    remote: int
    on_site: int
    top_locations: list[LocationCount] = Field(default_factory=list)
    dataset: str


class JobSeedResponse(BaseModel):
    dataset: str
    loaded: int
    updated: int
    total: int


class SkillDemandItem(BaseModel):
    skill: str
    required_count: int = 0
    preferred_count: int = 0
    count: int = 0
    jobs_demanding: list[str] = Field(default_factory=list)
    demand_level: str = "low"


class SkillDemandResponse(BaseModel):
    dataset: str
    total_jobs: int
    items: list[SkillDemandItem] = Field(default_factory=list)
    computed_from: str = "active curated job catalog"