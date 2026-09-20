"""Structured resume profile schemas for the Resume Intelligence Engine (Phase 1).

These models form the canonical internal representation of parsed resume
intelligence. They are Pydantic v2 models that serialize losslessly to JSON so
they can be persisted inside the existing ``parsed_resume_data.parsed_json``
column without any database migration.

Design rules:
- Missing information is ``None`` / empty lists. Nothing is invented.
- Dates keep both the original extracted string and a normalized ISO value.
- Source traceability: entities may carry ``source_section`` and a short
  ``source_text`` quote so later phases can ground matching/explanations.
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SkillCategory(str, Enum):
    """Simple, closed set of skill categories. Uncertain -> OTHER."""

    PROGRAMMING_LANGUAGE = "Programming Language"
    FRAMEWORK = "Framework"
    DATABASE = "Database"
    CLOUD = "Cloud"
    DEVOPS = "DevOps"
    AI_ML = "AI/ML"
    DATA = "Data"
    TESTING = "Testing"
    SECURITY = "Security"
    TOOL = "Tool"
    SOFT_SKILL = "Soft Skill"
    OTHER = "Other"


class NormalizedSkill(BaseModel):
    name: str
    category: str = SkillCategory.OTHER.value
    matched_on: str | None = None
    inferred: bool = False
    source_section: str | None = None
    source_text: str | None = None


class ExperienceEntry(BaseModel):
    company: str | None = None
    job_title: str | None = None
    title: str | None = None  # legacy alias of job_title (backward compatible)
    location: str | None = None
    employment_type: str | None = None
    start_date: str | None = None  # normalized ISO: "YYYY-MM" or "YYYY"
    end_date: str | None = None
    original_start_date: str | None = None
    original_end_date: str | None = None
    is_current: bool = False
    dates_uncertain: bool = False
    duration_months: int | None = None
    duration_label: str | None = None
    description: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    source_section: str | None = None
    source_text: str | None = None


class EducationEntry(BaseModel):
    institution: str | None = None
    degree: str | None = None
    field_of_study: str | None = None
    start_date: str | None = None  # normalized ISO
    end_date: str | None = None
    original_start_date: str | None = None
    original_end_date: str | None = None
    gpa: str | None = None
    raw_text: str | None = None  # legacy-compatible block quote (short)
    source_section: str | None = None


class ProjectEntry(BaseModel):
    name: str | None = None
    description: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    responsibilities: list[str] = Field(default_factory=list)
    achievements: list[str] = Field(default_factory=list)
    start_date: str | None = None
    end_date: str | None = None
    source_section: str | None = None
    source_text: str | None = None


class CertificationEntry(BaseModel):
    name: str
    issuer: str | None = None
    date: str | None = None  # original extracted string
    date_iso: str | None = None
    source_section: str | None = None


class LanguageEntry(BaseModel):
    language: str
    proficiency: str | None = None


class DetectedSectionInfo(BaseModel):
    section: str
    heading: str
    confidence: float = Field(ge=0.0, le=1.0)


class ProfileMetadata(BaseModel):
    parser_version: str
    processed_at: datetime
    language: str | None = None
    detected_sections: list[DetectedSectionInfo] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ResumeProfile(BaseModel):
    """Canonical structured output of the Resume Intelligence Engine."""

    schema_version: str = "1"
    summary: str | None = None
    personal_info: dict[str, Any] | None = None
    skills: list[NormalizedSkill] = Field(default_factory=list)
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    projects: list[ProjectEntry] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)
    metadata: ProfileMetadata
