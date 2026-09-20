import logging
from pathlib import Path
from typing import Any

from app.services.candidate.resume_parser.entity_extractors import (
    CertificationExtractor,
    EducationExtractor,
    ExperienceExtractor,
    LanguageExtractor,
    PersonalInfoExtractor,
    ProjectExtractor,
)
from app.services.candidate.resume_parser.section_parser import SectionParser
from app.services.candidate.resume_parser.skill_matcher import SkillMatcher
from app.services.candidate.resume_parser.text_extractor import TextExtractor

logger = logging.getLogger(__name__)


class ResumeParser:
    def __init__(self, file_path: str | Path) -> None:
        self.file_path = Path(file_path)
        self.raw_text: str = ""
        self.sections: dict[str, str] = {}
        self.parsed_data: dict[str, Any] = {}

    def parse(self) -> dict[str, Any]:
        self.raw_text = TextExtractor.extract(self.file_path)
        if not self.raw_text.strip():
            raise ValueError("No text could be extracted from the resume file")

        self._detect_language()
        self.sections = SectionParser.detect_sections(self.raw_text)
        self.parsed_data = {
            "raw_text": self.raw_text,
            "language": self.language,
            "personal_info": self._parse_personal_info(),
            "education": self._parse_education(),
            "experience": self._parse_experience(),
            "skills": self._parse_skills(),
            "projects": self._parse_projects(),
            "certifications": self._parse_certifications(),
            "languages": self._parse_languages(),
        }

        return self.parsed_data

    def _detect_language(self) -> None:
        self.language = TextExtractor.detect_language(self.raw_text)

    def _parse_personal_info(self) -> dict[str, Any]:
        section_text = self.sections.get("personal_info", "")
        return PersonalInfoExtractor.extract(self.raw_text, section_text)

    def _parse_education(self) -> list[dict[str, Any]]:
        section_text = self.sections.get("education", "")
        if not section_text:
            return []
        return EducationExtractor.extract(section_text)

    def _parse_experience(self) -> list[dict[str, Any]]:
        section_text = self.sections.get("experience", "")
        if not section_text:
            return []
        return ExperienceExtractor.extract(section_text)

    def _parse_skills(self) -> list[dict[str, Any]]:
        return SkillMatcher.extract_skills_from_sections(self.sections)

    def _parse_projects(self) -> list[dict[str, Any]]:
        section_text = self.sections.get("projects", "")
        if not section_text:
            return []
        return ProjectExtractor.extract(section_text)

    def _parse_certifications(self) -> list[dict[str, Any]]:
        section_text = self.sections.get("certifications", "")
        if not section_text:
            return []
        return CertificationExtractor.extract(section_text)

    def _parse_languages(self) -> list[dict[str, Any]]:
        section_text = self.sections.get("languages", "")
        if not section_text:
            return []
        return LanguageExtractor.extract(section_text)

    @staticmethod
    def parse_file(file_path: str | Path) -> dict[str, Any]:
        parser = ResumeParser(file_path)
        return parser.parse()
