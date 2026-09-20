"""Resume Intelligence Engine — Phase 1 orchestrator.

Pipeline (deterministic only, no LLM calls in this phase):

    file -> text extraction -> language detection
         -> intelligent section detection (synonyms + fuzzy + confidence)
         -> structured entity extraction (experience/projects v2)
         -> skill normalization & categorization (dedicated component)
         -> ResumeProfile (+ metadata: parser_version, processed_at,
            detected sections, warnings)

Also produces a fully backward-compatible ``parsed_data`` dict matching the
legacy ``ResumeParser`` shape so existing consumers (screening, profile sync,
demo generator, API responses) keep working unchanged.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.candidate.resume_parser.entity_extractors import PersonalInfoExtractor
from app.services.candidate.resume_parser.personal_info_sanitizer import (
    sanitize_personal_info,
)
from app.services.candidate.resume_parser.schemas import (
    ExperienceEntry,
    NormalizedSkill,
    ProfileMetadata,
    ProjectEntry,
    ResumeProfile,
)
from app.services.candidate.resume_parser.section_detector import IntelligentSectionParser
from app.services.candidate.resume_parser.skill_matcher import SkillMatcher
from app.services.candidate.resume_parser.skill_normalizer import SkillNormalizer
from app.services.candidate.resume_parser.structured_extractors import (
    CertificationMapper,
    EducationMapper,
    ExperienceExtractorV2,
    LanguageMapper,
    ProjectExtractorV2,
    SummaryExtractor,
)
from app.services.candidate.resume_parser.text_extractor import TextExtractor

logger = logging.getLogger(__name__)

PARSER_VERSION = "rie-1.0.0"

_SKILL_SECTION = "skills"


class ResumeIntelligenceEngine:
    """Parses a resume file into a structured ``ResumeProfile``."""

    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)

    def parse(self) -> tuple[ResumeProfile, dict[str, Any]]:
        """Returns ``(profile, legacy_compatible_parsed_data)``."""
        raw_text = TextExtractor.extract(self.file_path)
        if not raw_text.strip():
            raise ValueError("No text could be extracted from the resume file")

        language = TextExtractor.detect_language(raw_text)

        sections, detected_sections, warnings = IntelligentSectionParser.detect(raw_text)

        personal_info = sanitize_personal_info(
            PersonalInfoExtractor.extract(raw_text, sections.get("personal_info", ""))
        )

        skills = self._extract_skills(sections, warnings)
        experience = ExperienceExtractorV2.extract(sections.get("experience", ""))
        education = EducationMapper.extract(sections.get("education", ""))
        projects = ProjectExtractorV2.extract(sections.get("projects", ""))
        certifications = CertificationMapper.extract(sections.get("certifications", ""))
        languages = LanguageMapper.extract(sections.get("languages", ""))
        summary = SummaryExtractor.extract(
            sections.get("summary"), sections.get("objective")
        )

        if "experience" not in sections:
            warnings.append("No experience section detected")
        if not skills:
            warnings.append("No recognizable skills found")

        profile = ResumeProfile(
            summary=summary,
            personal_info=personal_info or None,
            skills=skills,
            experience=experience,
            education=education,
            projects=projects,
            certifications=certifications,
            languages=languages,
            metadata=ProfileMetadata(
                parser_version=PARSER_VERSION,
                processed_at=datetime.now(timezone.utc),
                language=language,
                detected_sections=detected_sections,
                warnings=warnings,
            ),
        )

        parsed_data = self._build_legacy_dict(
            raw_text=raw_text,
            language=language,
            sections=sections,
            personal_info=personal_info,
            skills=skills,
            profile=profile,
        )
        return profile, parsed_data

    # ------------------------------------------------------------------
    # Skills
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_skills(
        sections: dict[str, str], warnings: list[str]
    ) -> list[NormalizedSkill]:
        declared: list[NormalizedSkill] = []
        seen: set[str] = set()

        skills_text = sections.get(_SKILL_SECTION, "")
        if skills_text:
            for found in SkillMatcher.extract_skills(skills_text):
                normalized = (
                    SkillNormalizer.normalize(str(found["name"]))
                    or NormalizedSkill(name=str(found["name"]), category="Other")
                )
                normalized.matched_on = str(found.get("matched_on"))
                normalized.inferred = False
                normalized.source_section = _SKILL_SECTION
                if normalized.name.lower() not in seen:
                    seen.add(normalized.name.lower())
                    declared.append(normalized)
        else:
            warnings.append("No dedicated skills section detected; inferring from context")

        # Contextual inference per section keeps source traceability.
        for section_name, body in sections.items():
            if section_name == _SKILL_SECTION or not body.strip():
                continue
            for found in SkillMatcher.extract_skills(body):
                normalized = (
                    SkillNormalizer.normalize(str(found["name"]))
                    or NormalizedSkill(name=str(found["name"]), category="Other")
                )
                normalized.matched_on = str(found.get("matched_on"))
                normalized.source_section = section_name
                if normalized.name.lower() in seen:
                    continue
                normalized.inferred = True
                seen.add(normalized.name.lower())
                declared.append(normalized)

        return declared

    # ------------------------------------------------------------------
    # Backward compatibility
    # ------------------------------------------------------------------

    @staticmethod
    def _build_legacy_dict(
        raw_text: str,
        language: str | None,
        sections: dict[str, str],
        personal_info: dict[str, Any],
        skills: list[NormalizedSkill],
        profile: ResumeProfile,
    ) -> dict[str, Any]:
        """Shape-compatible with the legacy ``ResumeParser.parse()`` output.

        Legacy consumers read: personal_info fields, education dicts
        (institution/degree/field/gpa), experience dicts
        (title/company/start_date/end_date/description/raw_text), project dicts
        (name/description/technologies), certification/language dicts, and the
        skills list ({name, matched_on, category[, inferred]}).
        """
        legacy_education = []
        for edu in profile.education:
            item: dict[str, Any] = {}
            if edu.institution:
                item["institution"] = edu.institution
            if edu.degree:
                item["degree"] = edu.degree
            if edu.field_of_study:
                item["field"] = edu.field_of_study
            if edu.original_start_date:
                item["start_date"] = edu.original_start_date
            if edu.original_end_date:
                item["end_date"] = edu.original_end_date
            if edu.gpa:
                item["gpa"] = edu.gpa
            if item:
                item["raw_text"] = edu.raw_text or ""
                legacy_education.append(item)

        legacy_experience = []
        for exp in profile.experience:
            legacy_experience.append(
                {
                    "title": exp.job_title,
                    "job_title": exp.job_title,
                    "company": exp.company,
                    "location": exp.location,
                    "employment_type": exp.employment_type,
                    "start_date": exp.original_start_date,
                    "end_date": exp.original_end_date,
                    "start_date_iso": exp.start_date,
                    "end_date_iso": exp.end_date,
                    "is_current": exp.is_current,
                    "dates_uncertain": exp.dates_uncertain,
                    "duration_months": exp.duration_months,
                    "duration_label": exp.duration_label,
                    "description": exp.description,
                    "responsibilities": exp.responsibilities,
                    "achievements": exp.achievements,
                    "technologies": exp.technologies,
                    "source_section": exp.source_section,
                    "source_text": exp.source_text,
                }
            )

        legacy_projects = [
            {
                "name": p.name,
                "description": p.description,
                "technologies": p.technologies,
                "responsibilities": p.responsibilities,
                "achievements": p.achievements,
                "start_date": p.start_date,
                "end_date": p.end_date,
                "source_section": p.source_section,
                "source_text": p.source_text,
            }
            for p in profile.projects
        ]

        legacy_certifications = [
            {"name": c.name, "issuer": c.issuer} for c in profile.certifications
        ]
        legacy_languages = [
            {"language": l.language, "proficiency": l.proficiency}
            for l in profile.languages
        ]

        legacy_skills: list[dict[str, Any]] = []
        for skill in skills:
            db_category = SkillMatcher._get_category(skill.name.lower())
            item = {
                "name": skill.name.lower(),
                "display_name": skill.name,  # already display-cased by the normalizer
                "matched_on": skill.matched_on,
                "category": db_category,
                "friendly_category": skill.category,
                "source_section": skill.source_section,
            }
            if skill.inferred:
                item["inferred"] = True
            legacy_skills.append(item)

        return {
            "raw_text": raw_text,
            "language": language,
            "personal_info": personal_info,
            "education": legacy_education,
            "experience": legacy_experience,
            "skills": legacy_skills,
            "projects": legacy_projects,
            "certifications": legacy_certifications,
            "languages": legacy_languages,
            "summary": profile.summary,
            "sections_detected": {
                info.section: {"heading": info.heading, "confidence": info.confidence}
                for info in profile.metadata.detected_sections
            },
            "parser_metadata": profile.metadata.model_dump(mode="json"),
        }

    @staticmethod
    def parse_file(file_path: str | Path) -> tuple[ResumeProfile, dict[str, Any]]:
        engine = ResumeIntelligenceEngine(file_path)
        return engine.parse()
