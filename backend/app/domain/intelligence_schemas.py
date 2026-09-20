import uuid
from datetime import date, datetime

from pydantic import BaseModel


class SkillSummaryItem(BaseModel):
    name: str
    category: str
    proficiency: str | None = None
    years: float | None = None


class CandidateIntelligence(BaseModel):
    profile_id: uuid.UUID
    total_experience_years: float
    total_experience_months: int
    highest_qualification: str | None
    education_level: str
    skill_summary: list[SkillSummaryItem]
    skills_by_category: dict[str, list[str]]
    project_count: int
    certification_count: int
    language_count: int
    profile_strength: int
    missing_sections: list[str]
    recommendations: list[str]

    model_config = {"from_attributes": True}


class SyncDiffItem(BaseModel):
    section: str
    field: str
    parsed_value: str | None
    profile_value: str | None
    status: str = "pending"


class SyncDiffResponse(BaseModel):
    resume_id: uuid.UUID
    personal_info: list[SyncDiffItem] = []
    education: list[SyncDiffItem] = []
    experience: list[SyncDiffItem] = []
    skills: list[SyncDiffItem] = []
    projects: list[SyncDiffItem] = []
    certifications: list[SyncDiffItem] = []
    languages: list[SyncDiffItem] = []

    model_config = {"from_attributes": True}


class SyncActionRequest(BaseModel):
    resume_id: uuid.UUID
    section: str
    action: str
    item_index: int | None = None
    field: str | None = None


class SyncActionResult(BaseModel):
    message: str
    applied: int = 0


class ResumeVersionResponse(BaseModel):
    id: uuid.UUID
    version: int
    original_filename: str
    file_size: int
    file_type: str
    status: str
    is_primary: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeCompareResponse(BaseModel):
    versions: list[ResumeVersionResponse]
    diffs: list[dict] = []

    model_config = {"from_attributes": True}
