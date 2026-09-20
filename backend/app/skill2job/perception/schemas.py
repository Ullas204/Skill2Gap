"""Perception schemas (Phase 2).

Structured, provenance-aware representation of candidate perception inputs.
Every extracted entity carries its source and grounding so downstream agents
(profile, matching, skill-gap, opportunity) can trust or discard it.

Design rules:
- Nothing is invented. Empty lists / ``None`` mean "not perceived".
- ``confidence`` reflects extraction certainty, not model guesses.
- ``processing_status`` is ``ok`` | ``partial`` | ``failed``. Voice/image
  inputs without a configured provider fail gracefully (never fake output).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    source: str = Field(..., description="resume | free_text | voice | image | document")
    section: str | None = None
    evidence: str | None = Field(None, description="short quote grounding the extraction")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    method: str | None = None


class PerceptionSkill(BaseModel):
    name: str
    canonical: str | None = None
    category: str | None = None
    inferred: bool = False
    provenance: Provenance | None = None


class PerceptionEducation(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    raw_text: str | None = None
    provenance: Provenance | None = None


class PerceptionExperience(BaseModel):
    company: str | None = None
    job_title: str | None = None
    location: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    is_current: bool = False
    duration_months: int | None = None
    description: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    provenance: Provenance | None = None


class PerceptionProject(BaseModel):
    name: str | None = None
    description: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    provenance: Provenance | None = None


class PerceptionCertification(BaseModel):
    name: str | None = None
    issuer: str | None = None
    date: str | None = None
    provenance: Provenance | None = None


class PerceptionLanguage(BaseModel):
    language: str | None = None
    proficiency: str | None = None
    provenance: Provenance | None = None


class PerceptionError(BaseModel):
    """Structured error with stage, code, and recoverability."""
    code: str
    message: str
    stage: str | None = None
    recoverable: bool = False


class ParsingQuality(BaseModel):
    """Quality metrics for the parsing pipeline."""
    text_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    layout_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    entity_quality: float = Field(default=0.0, ge=0.0, le=1.0)
    overall_confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class DocumentInfo(BaseModel):
    """Metadata about the source document."""
    type: str | None = None
    format: str | None = None
    pages: int | None = None
    is_scanned: bool = False
    ocr_used: bool = False
    extraction_method: str | None = None
    tables_found: int = 0


class PerceptionResult(BaseModel):
    """Canonical output of the Perception pipeline."""

    input_type: str
    parser_version: str
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    extracted_text: str | None = None
    summary: str | None = None
    skills: list[PerceptionSkill] = Field(default_factory=list)
    education: list[PerceptionEducation] = Field(default_factory=list)
    experience: list[PerceptionExperience] = Field(default_factory=list)
    projects: list[PerceptionProject] = Field(default_factory=list)
    certifications: list[PerceptionCertification] = Field(default_factory=list)
    languages: list[PerceptionLanguage] = Field(default_factory=list)
    interests: list[str] = Field(default_factory=list)
    target_roles: list[str] = Field(default_factory=list)
    location: str | None = None
    field_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    provenance: list[Provenance] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[PerceptionError] = Field(default_factory=list)
    processing_status: str = "ok"
    processing_message: str | None = None
    document: DocumentInfo | None = None
    quality: ParsingQuality | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class PerceptionUploadResponse(BaseModel):
    perception_id: str
    result: PerceptionResult


class PerceptionTextResponse(BaseModel):
    perception_id: str
    result: PerceptionResult


class SpeechToTextStatus(BaseModel):
    configured: bool
    providers: list[str]


class OcrStatus(BaseModel):
    configured: bool
    providers: list[str]