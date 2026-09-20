"""Pydantic schemas for the AI Demo Data Generator & Recruitment Simulation Platform."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class DemoGenerateRequest(BaseModel):
    scenario_slug: str | None = None
    num_candidates: int = Field(default=20, ge=1, le=100)
    num_recruiters: int = Field(default=3, ge=0, le=20)
    num_hr: int = Field(default=1, ge=0, le=10)
    num_jobs: int = Field(default=5, ge=1, le=30)
    num_companies: int | None = Field(default=None, ge=1, le=20)
    candidates_per_job: int = Field(default=8, ge=1, le=100)
    hiring_difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    skill_categories: list[str] = Field(default_factory=list, max_length=8)
    include_screening: bool = True
    include_interviews: bool = True
    include_reports: bool = True
    include_agent_indexing: bool = True
    resume_format: str = Field(default="mixed", pattern="^(pdf|docx|txt|mixed)$")
    seed: int | None = Field(default=None, ge=0)


class DemoCustomRequest(BaseModel):
    companies: list[str] = Field(default_factory=list, max_length=20)
    job_titles: list[str] = Field(default_factory=list, max_length=50)
    num_candidates: int = Field(default=20, ge=1, le=100)
    num_recruiters: int = Field(default=3, ge=0, le=20)
    num_hr: int = Field(default=1, ge=0, le=10)
    num_jobs: int = Field(default=5, ge=1, le=30)
    num_companies: int | None = Field(default=None, ge=1, le=20)
    candidates_per_job: int = Field(default=8, ge=1, le=100)
    hiring_difficulty: str = Field(default="medium", pattern="^(easy|medium|hard)$")
    skill_categories: list[str] = Field(default_factory=list, max_length=8)
    include_screening: bool = True
    include_interviews: bool = True
    include_reports: bool = True
    include_agent_indexing: bool = True
    resume_format: str = Field(default="mixed", pattern="^(pdf|docx|txt|mixed)$")
    seed: int | None = Field(default=None, ge=0)


class DemoRunResponse(BaseModel):
    id: uuid.UUID
    scenario_id: uuid.UUID | None = None
    status: str
    progress: int
    current_stage: str | None = None
    stage_message: str | None = None
    stats: dict | None = None
    error: str | None = None
    created_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


class DemoEventResponse(BaseModel):
    id: uuid.UUID
    stage: str | None = None
    event_type: str
    message: str
    details: dict | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class DemoRunDetailResponse(BaseModel):
    run: DemoRunResponse
    events: list[DemoEventResponse] = []


class DemoScenarioResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    description: str | None = None
    is_active: bool
    config: dict | None = None
    tags: list | None = None

    model_config = {"from_attributes": True}


class DemoStatusResponse(BaseModel):
    latest_run: DemoRunResponse | None = None
    runs: list[DemoRunResponse] = []
    totals: dict = {}


class DemoExportResponse(BaseModel):
    generated_at: datetime
    companies: list[dict] = []
    users: list[dict] = []
    jobs: list[dict] = []
    applications: list[dict] = []
    screenings: list[dict] = []
    interviews: list[dict] = []
    reports: list[dict] = []
    summary: dict = {}
