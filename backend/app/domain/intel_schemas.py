"""Response schemas for Candidate Evidence Intelligence (Phase 3).

Design rules carried over from Phase 2:
- NO EVIDENCE = NO CLAIM: absence of evidence is reported as such, never as
  a statement that the candidate lacks a skill.
- Confidence describes OUR EVIDENCE, not the candidate's probability of
  being good. There is no universal candidate quality score anywhere here.
- Review flags are neutral observations for human recruiters. They are never
  accusations and always come with possible legitimate explanations.
- Achievements are labelled "Candidate-stated": we did not verify them.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.fit_schemas import EvidenceItem

SkillDepth = Literal[
    "expert_level_evidence", "strong", "moderate",
    "limited", "mention_only", "no_evidence",
]
EvidenceConfidence = Literal["high", "medium", "low", "insufficient"]
FlagSeverity = Literal["info", "warning"]
FlagType = Literal[
    "stated_vs_timeline_mismatch",
    "overlapping_employment",
    "date_inconsistency",
    "missing_dates",
    "employment_gap",
]


class ProfileSnapshot(BaseModel):
    """Factual counts derived from structured resume data."""

    total_experience_months: int = 0
    total_experience_years: float | None = None
    experience_count: int = 0
    project_count: int = 0
    certification_count: int = 0
    education_count: int = 0
    skills_mentioned: int = 0
    highest_degree: str | None = None


class SkillAssessment(BaseModel):
    """Depth-of-evidence assessment for one skill."""

    skill: str
    category: str | None = None
    depth: SkillDepth
    confidence: EvidenceConfidence
    professional_months: int = 0
    counts: dict[str, int] = Field(default_factory=dict)
    reason: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class StrengthInsight(BaseModel):
    """An evidence-backed candidate strength."""

    title: str
    category: str | None = None
    depth: SkillDepth
    confidence: EvidenceConfidence
    reason: str
    evidence: list[EvidenceItem] = Field(default_factory=list)


class AchievementInsight(BaseModel):
    """A self-reported achievement, explicitly labelled as unverified."""

    text: str = Field(min_length=1)
    context: str | None = None
    source_type: Literal["experience", "project"]
    label: str = "Candidate-stated"


class ReviewFlag(BaseModel):
    """A neutral timeline observation for human review — never an accusation."""

    flag_type: FlagType
    severity: FlagSeverity
    title: str
    description: str
    possible_explanation: str | None = None
    evidence: list[EvidenceItem] = Field(default_factory=list)


class ScreeningQuestionSuggestion(BaseModel):
    """An interview question grounded in specific resume evidence."""

    question: str = Field(min_length=1)
    topic: str
    reason: str


class EvidenceGapInsight(BaseModel):
    """A skill mentioned without meaningful supporting evidence."""

    skill: str
    current_depth: SkillDepth
    note: str


class IntelSummary(BaseModel):
    text: str
    source: Literal["deterministic", "llm_polished"]
    disclaimer: str = (
        "AI-assisted evidence analysis based on resume content. "
        "This is decision support, not a hiring decision."
    )


class TimelineInfo(BaseModel):
    computed_months: int
    stated_years_found: bool
    stated_years_value: float | None = None
    entries_with_dates: int
    entries_total: int


class EvidenceIntelligenceResponse(BaseModel):
    candidate_id: str
    candidate_name: str
    resume_id: str | None = None
    engine_version: str
    cached: bool = False
    snapshot: ProfileSnapshot
    timeline: TimelineInfo
    strengths: list[StrengthInsight] = Field(default_factory=list)
    skill_assessments: list[SkillAssessment] = Field(default_factory=list)
    achievements: list[AchievementInsight] = Field(default_factory=list)
    review_flags: list[ReviewFlag] = Field(default_factory=list)
    evidence_gaps: list[EvidenceGapInsight] = Field(default_factory=list)
    screening_questions: list[ScreeningQuestionSuggestion] = Field(default_factory=list)
    summary: IntelSummary


class JobContextBlock(BaseModel):
    """Job-specific contextual intelligence composed over the cached fit result."""

    job_id: str
    job_title: str
    fit_classification: str
    fit_score: int
    required_years: float | None = None
    relevant_years: float | None = None
    total_years: float | None = None
    relevance_basis: str | None = None
    requirement_gaps: list[str] = Field(default_factory=list)
    requirement_unknown: list[str] = Field(default_factory=list)
    additional_questions: list[ScreeningQuestionSuggestion] = Field(default_factory=list)
    summary: IntelSummary


class JobIntelligenceResponse(BaseModel):
    candidate_id: str
    candidate_name: str
    job_id: str
    job_title: str
    engine_version: str
    cached: bool = False
    candidate_intelligence: EvidenceIntelligenceResponse
    job_context: JobContextBlock
