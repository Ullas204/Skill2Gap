import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.resume_intelligence_schemas import (
    ATSReport,
    IndustryKeywordSuggestions,
    KeywordAnalysisReport,
    Recommendation,
    ResumeCompareItem,
    ResumeCompareReport,
    ResumeIntelligenceReport,
    ResumeIntelligenceScores,
    ScoreDetail,
    SkillAnalysisReport,
)
from app.repositories.candidate.resume import ParsedResumeDataRepository, ResumeRepository
from app.services.candidate.resume_analysis import ResumeAnalysisEngine

logger = __import__("logging").getLogger(__name__)


class ResumeIntelligenceService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._resume_repo = ResumeRepository(session)
        self._parsed_repo = ParsedResumeDataRepository(session)

    async def get_full_report(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> ResumeIntelligenceReport:
        resume = await self._resume_repo.get_by_user(resume_id, user_id)
        if not resume:
            raise NotFoundError(detail="Resume not found")

        parsed = await self._parsed_repo.get_by_resume(resume_id)
        parsed_data = self._parsed_to_dict(parsed) if parsed else {}

        analysis = ResumeAnalysisEngine.analyze(parsed_data)

        scores = ResumeIntelligenceScores(
            overall=ScoreDetail(score=analysis["quality_score"], label="Overall Resume Score", description="Based on section presence and quality"),
            completeness=ScoreDetail(score=analysis["completeness_score"], label="Completeness", description="How complete each section is"),
            readability=ScoreDetail(score=analysis["readability_score"], label="Readability", description="Sentence structure and formatting"),
            professionalism=ScoreDetail(score=analysis["professionalism_score"], label="Professionalism", description="Action verbs and quantifiable achievements"),
            keyword_optimization=ScoreDetail(score=analysis["keyword_optimization_score"], label="Keyword Optimization", description="Industry keyword usage"),
            ats_compatibility=ScoreDetail(score=analysis["ats_score"], label="ATS Compatibility", description="Applicant Tracking System friendliness"),
        )

        recommendations = [
            Recommendation(category="improvement", text=r, priority="high" if i < 5 else "medium")
            for i, r in enumerate(analysis.get("recommendations", []))
        ]

        sk = analysis.get("skill_analysis", {})
        skill_analysis = SkillAnalysisReport(**sk)

        kw = analysis.get("keyword_analysis", {})
        keyword_analysis = KeywordAnalysisReport(**kw)

        ats_report = ATSReport(
            score=analysis["ats_score"],
            formatting_issues=analysis.get("formatting_issues", []),
            sections_valid={s: analysis.get("section_scores", {}).get(s, 0) > 0 for s in ["personal_info", "education", "experience", "skills", "projects"]},
            contact_info_found={},
            has_email="@" in parsed_data.get("raw_text", ""),
            has_phone=bool(__import__("re").search(r'[\+\d\s\-\(\)]{7,}', parsed_data.get("raw_text", ""))),
            has_linkedin="linkedin" in parsed_data.get("raw_text", "").lower(),
            has_github="github" in parsed_data.get("raw_text", "").lower(),
            resume_length="medium",
            file_format_ok=True,
            section_count=sum(1 for v in analysis.get("section_scores", {}).values() if v > 0),
            action_verb_count=kw.get("matched_action_keywords", 0),
            quantifiable_achievements=len(__import__("re").findall(r'\d+%|\$\d+|\d+x', parsed_data.get("raw_text", "").lower())),
        )

        industry_keywords = {}
        for cat, data in analysis.get("industry_keywords", {}).items():
            industry_keywords[cat] = IndustryKeywordSuggestions(category=cat, **data)

        return ResumeIntelligenceReport(
            resume_id=resume_id,
            filename=resume.original_filename,
            scores=scores,
            strengths=analysis.get("strengths", []),
            weaknesses=analysis.get("weaknesses", []),
            recommendations=recommendations,
            skill_analysis=skill_analysis,
            keyword_analysis=keyword_analysis,
            ats_report=ats_report,
            industry_keywords=industry_keywords,
            generated_at=datetime.now(timezone.utc),
        )

    async def compare_versions(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> ResumeCompareReport:
        resume = await self._resume_repo.get_by_user(resume_id, user_id)
        if not resume:
            raise NotFoundError(detail="Resume not found")

        def build_item(r, parsed_data_dict) -> ResumeCompareItem:
            analysis = ResumeAnalysisEngine.analyze(parsed_data_dict)
            return ResumeCompareItem(
                version=r.version,
                filename=r.original_filename,
                scores=ResumeIntelligenceScores(
                    overall=ScoreDetail(score=analysis["quality_score"], label="Overall", description=""),
                    completeness=ScoreDetail(score=analysis["completeness_score"], label="Completeness", description=""),
                    readability=ScoreDetail(score=analysis["readability_score"], label="Readability", description=""),
                    professionalism=ScoreDetail(score=analysis["professionalism_score"], label="Professionalism", description=""),
                    keyword_optimization=ScoreDetail(score=analysis["keyword_optimization_score"], label="Keywords", description=""),
                    ats_compatibility=ScoreDetail(score=analysis["ats_score"], label="ATS", description=""),
                ),
                strengths=analysis.get("strengths", []),
                weaknesses=analysis.get("weaknesses", []),
                total_skills=len(analysis.get("skill_analysis", {}).get("skill_names", [])),
                created_at=r.created_at,
            )

        parsed = await self._parsed_repo.get_by_resume(resume_id)
        current_data = self._parsed_to_dict(parsed) if parsed else {}
        current_item = build_item(resume, current_data)

        all_resumes = await self._resume_repo.list_by_user(user_id)
        previous = None
        prev_resume = None
        for r in all_resumes:
            if r.id != resume_id and r.created_at < resume.created_at:
                if prev_resume is None or r.created_at > prev_resume.created_at:
                    prev_resume = r

        if prev_resume:
            prev_parsed = await self._parsed_repo.get_by_resume(prev_resume.id)
            prev_data = self._parsed_to_dict(prev_parsed) if prev_parsed else {}
            previous = build_item(prev_resume, prev_data)

        score_changes = {}
        if previous:
            for field in ("overall", "completeness", "readability", "professionalism", "keyword_optimization", "ats_compatibility"):
                curr_val = getattr(current_item.scores, field).score
                prev_val = getattr(previous.scores, field).score
                score_changes[field] = curr_val - prev_val

        current_skills = set()
        if parsed and parsed.skills:
            for s in parsed.skills:
                if isinstance(s, dict):
                    current_skills.add(s.get("name", s.get("skill", "")))
        prev_skills = set()
        if prev_resume and prev_parsed and prev_parsed.skills:
            for s in prev_parsed.skills:
                if isinstance(s, dict):
                    prev_skills.add(s.get("name", s.get("skill", "")))

        skills_added = list(current_skills - prev_skills)
        skills_removed = list(prev_skills - current_skills)

        return ResumeCompareReport(
            current=current_item,
            previous=previous,
            score_changes=score_changes,
            skills_added=skills_added,
            skills_removed=skills_removed,
        )

    def _parsed_to_dict(self, parsed) -> dict:
        return {
            "raw_text": parsed.raw_text or "",
            "personal_info": parsed.personal_info or {},
            "education": parsed.education or [],
            "experience": parsed.experience or [],
            "skills": parsed.skills or [],
            "projects": parsed.projects or [],
            "certifications": parsed.certifications or [],
            "languages": parsed.languages or [],
        }
