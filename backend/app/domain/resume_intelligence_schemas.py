import uuid
from datetime import datetime

from pydantic import BaseModel


class ScoreDetail(BaseModel):
    score: int
    max_score: int = 100
    label: str
    description: str = ""


class ResumeIntelligenceScores(BaseModel):
    overall: ScoreDetail
    completeness: ScoreDetail
    readability: ScoreDetail
    professionalism: ScoreDetail
    keyword_optimization: ScoreDetail
    ats_compatibility: ScoreDetail


class SkillAnalysisReport(BaseModel):
    skill_names: list[str] = []
    total_skills: int = 0
    categorized: dict[str, list[str]] = {}
    duplicates: list[str] = []
    missing_essential: list[str] = []
    suggestions: list[str] = []


class KeywordAnalysisReport(BaseModel):
    action_keywords_found: list[str] = []
    action_keywords_missing: list[str] = []
    total_action_keywords: int = 0
    matched_action_keywords: int = 0
    keyword_density: dict[str, int] = {}


class ATSReport(BaseModel):
    score: int = 0
    formatting_issues: list[str] = []
    sections_valid: dict[str, bool] = {}
    contact_info_found: dict[str, bool] = {}
    has_email: bool = False
    has_phone: bool = False
    has_linkedin: bool = False
    has_github: bool = False
    resume_length: str = ""
    file_format_ok: bool = True
    section_count: int = 0
    action_verb_count: int = 0
    quantifiable_achievements: int = 0


class Recommendation(BaseModel):
    category: str
    text: str
    priority: str = "medium"


class IndustryKeywordSuggestions(BaseModel):
    category: str
    matched: list[str] = []
    suggested: list[str] = []


class ResumeIntelligenceReport(BaseModel):
    resume_id: uuid.UUID
    filename: str = ""
    scores: ResumeIntelligenceScores
    strengths: list[str] = []
    weaknesses: list[str] = []
    recommendations: list[Recommendation] = []
    skill_analysis: SkillAnalysisReport
    keyword_analysis: KeywordAnalysisReport
    ats_report: ATSReport
    industry_keywords: dict[str, IndustryKeywordSuggestions] = {}
    generated_at: datetime


class ResumeCompareItem(BaseModel):
    version: int
    filename: str = ""
    scores: ResumeIntelligenceScores
    strengths: list[str] = []
    weaknesses: list[str] = []
    total_skills: int = 0
    created_at: datetime


class ResumeCompareReport(BaseModel):
    current: ResumeCompareItem
    previous: ResumeCompareItem | None = None
    score_changes: dict[str, int] = {}
    skills_added: list[str] = []
    skills_removed: list[str] = []
