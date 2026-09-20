import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ResumeUploadResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_size: int
    file_type: str
    status: str
    is_primary: bool
    version: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    original_filename: str
    file_size: int
    file_type: str
    status: str
    language: str | None
    is_primary: bool
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeDetailResponse(BaseModel):
    resume: ResumeResponse
    parsed_data: "ParsedDataResponse | None" = None
    analysis: "ResumeAnalysisResponse | None" = None


class ParsedDataResponse(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    personal_info: dict | None
    education: list | None
    experience: list | None
    skills: list | None
    projects: list | None
    certifications: list | None
    languages: list | None
    summary: str | None = None
    resume_profile: dict | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeAnalysisResponse(BaseModel):
    id: uuid.UUID
    resume_id: uuid.UUID
    quality_score: int
    completeness_score: int = 0
    readability_score: int = 0
    professionalism_score: int = 0
    keyword_optimization_score: int = 0
    ats_score: int
    missing_sections: list | None
    recommendations: list | None
    section_scores: dict | None
    keyword_analysis: dict | None
    formatting_issues: list | None
    skill_analysis: dict | None = None
    industry_keywords: dict | None = None
    strengths: list | None = None
    weaknesses: list | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class ResumeSetPrimary(BaseModel):
    resume_id: uuid.UUID


ResumeDetailResponse.model_rebuild()


class ParsedField(BaseModel):
    field: str
    value: str | None
    confidence: float = Field(ge=0, le=1)
    source: str = "parsed"


class ParsedReviewItem(BaseModel):
    section: str
    extracted: list[dict]
    accepted: bool = False
    rejected: bool = False
    merged: bool = False


class ParsedReview(BaseModel):
    personal_info: list[ParsedField] = []
    education: list[ParsedField] = []
    experience: list[ParsedField] = []
    skills: list[ParsedField] = []
    projects: list[ParsedField] = []
    certifications: list[ParsedField] = []
    languages: list[ParsedField] = []

    model_config = {"from_attributes": True}


class ResumeStatusResponse(BaseModel):
    id: uuid.UUID
    status: str
    progress: int = 0


class ParsingStatusResponse(BaseModel):
    resume_id: uuid.UUID
    status: str
    progress: int
    message: str | None = None
