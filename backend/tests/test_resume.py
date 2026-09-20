"""Tests for resume upload, parsing, and analysis."""

import hashlib
import uuid

import pytest
from pathlib import Path

from app.domain.enums import ResumeStatus
from app.domain.models import CandidateProfile, Resume
from app.services.candidate.resume import ResumeService
from app.services.candidate.resume_analysis import ResumeAnalysisEngine
from app.services.candidate.resume_parser.parser import ResumeParser
from app.services.candidate.resume_parser.section_parser import SectionParser
from app.services.candidate.resume_parser.text_extractor import TextExtractor
from app.services.candidate.resume_parser.entity_extractors import (
    CertificationExtractor,
    EducationExtractor,
    ExperienceExtractor,
    LanguageExtractor,
    PersonalInfoExtractor,
    ProjectExtractor,
)
from app.services.candidate.resume_parser.skill_matcher import SkillMatcher


SAMPLE_RESUME_TEXT = """John Doe
john.doe@example.com | +1 555-123-4567
linkedin.com/in/johndoe

EXPERIENCE
Senior Software Engineer | Tech Corp Inc.
Jan 2020 - Present
• Led development of microservices architecture serving 1M+ users
• Implemented CI/CD pipeline reducing deployment time by 60%
• Mentored team of 5 junior engineers
• Built RESTful APIs using FastAPI and PostgreSQL

Software Engineer | StartupXYZ
June 2017 - Dec 2019
• Developed React-based dashboard with real-time analytics
• Optimized database queries improving performance by 40%
• Collaborated on Agile team with 8 engineers

EDUCATION
Master of Science in Computer Science
Stanford University
2015 - 2017
GPA: 3.9

Bachelor of Technology in Computer Science
Indian Institute of Technology
2011 - 2015

SKILLS
Python, JavaScript, TypeScript, React, FastAPI, PostgreSQL, Docker, Kubernetes,
AWS, CI/CD, Git, REST APIs, GraphQL, Machine Learning, TensorFlow

CERTIFICATIONS
AWS Certified Solutions Architect
Certified Kubernetes Administrator (CKA)

PROJECTS
E-Commerce Platform
Built full-stack e-commerce platform using React, Node.js, PostgreSQL
Technologies: React, Node.js, PostgreSQL, Docker

LANGUAGES
English (Native)
Hindi (Native)
Spanish (Intermediate)
"""


class TestResumeParser:
    def test_full_parse_end_to_end(self, tmp_path: Path) -> None:
        file_path = tmp_path / "resume.txt"
        file_path.write_text(SAMPLE_RESUME_TEXT, encoding="utf-8")

        parser = ResumeParser(file_path)
        result = parser.parse()

        assert result["language"] == "en"
        assert "personal_info" in parser.sections
        assert "experience" in parser.sections
        assert "education" in parser.sections
        assert "skills" in parser.sections

        pi = result["personal_info"]
        assert pi.get("name") == "John Doe"
        assert pi.get("email") == "john.doe@example.com"

        edu = result["education"]
        assert len(edu) >= 1

        exp = result["experience"]
        assert len(exp) >= 1
        assert any("Senior Software Engineer" in e.get("title", "") for e in exp)

        skills = result["skills"]
        assert len(skills) >= 5
        skill_names = [s["name"].lower() for s in skills]
        assert "python" in skill_names
        assert "react" in skill_names
        assert "docker" in skill_names
        assert "kubernetes" in skill_names

        certs = result["certifications"]
        assert any("AWS" in c.get("name", "") for c in certs)

        projects = result["projects"]
        assert any("E-Commerce" in p.get("name", "") for p in projects)


class TestTextExtractor:
    def test_extract_text(self, tmp_path: Path) -> None:
        file_path = tmp_path / "test.txt"
        file_path.write_text("Hello World", encoding="utf-8")
        text = TextExtractor.extract(file_path)
        assert text == "Hello World"

    def test_unsupported_extension(self) -> None:
        with pytest.raises(ValueError, match="Unsupported file extension"):
            TextExtractor.extract_bytes(b"test", ".xyz")

    def test_detect_language_english(self) -> None:
        lang = TextExtractor.detect_language("This is a sample English text")
        assert lang == "en"


class TestSectionParser:
    def test_detect_experience_section(self) -> None:
        text = "EXPERIENCE\nWorked at company\nSKILLS\nPython, Java"
        sections = SectionParser.detect_sections(text)
        assert "experience" in sections
        assert "skills" in sections

    def test_extract_bullet_points(self) -> None:
        text = "• First bullet\n• Second bullet\n- Third bullet"
        bullets = SectionParser.extract_bullet_points(text)
        assert len(bullets) == 3

    def test_extract_date_range(self) -> None:
        text = "Jan 2020 - Present"
        start, end = SectionParser.extract_date_range(text)
        assert start is not None
        assert "present" in end.lower() if end else False


class TestPersonalInfoExtractor:
    def test_extract_email(self) -> None:
        text = "Contact me at test@example.com or call +1 555-123-4567"
        result = PersonalInfoExtractor.extract(text)
        assert result.get("email") == "test@example.com"

    def test_extract_name(self) -> None:
        text = "John Doe\nSoftware Engineer"
        result = PersonalInfoExtractor.extract(text)
        assert result.get("name") == "John Doe"

    def test_extract_linkedin(self) -> None:
        text = "linkedin.com/in/johndoe"
        result = PersonalInfoExtractor.extract(text)
        assert "linkedin" in result


class TestEducationExtractor:
    def test_extract_degree(self) -> None:
        text = "Master of Science in Computer Science\nStanford University\n2015-2017"
        result = EducationExtractor.extract(text)
        assert len(result) >= 1
        assert "degree" in result[0]

    def test_extract_institution(self) -> None:
        text = "Bachelor of Technology\nIndian Institute of Technology\n2011-2015"
        result = EducationExtractor.extract(text)
        found = any(
            "Indian Institute" in e.get("institution", "") for e in result
        )
        assert found


class TestExperienceExtractor:
    def test_extract_experience(self) -> None:
        text = "Senior Engineer | Acme Inc\nJan 2020 - Present\n• Led team\n• Built product"
        result = ExperienceExtractor.extract(text)
        assert len(result) >= 1

    def test_extract_title(self) -> None:
        text = "Software Engineer | Company\n• Did things"
        result = ExperienceExtractor.extract(text)
        assert any("Software Engineer" in e.get("title", "") for e in result)


class TestSkillMatcher:
    def test_extract_skills(self) -> None:
        text = "I know Python, JavaScript, Docker, and Kubernetes"
        skills = SkillMatcher.extract_skills(text)
        names = [s["name"].lower() for s in skills]
        assert "python" in names
        assert "javascript" in names
        assert "docker" in names
        assert "kubernetes" in names

    def test_calculate_skill_score(self) -> None:
        skills = [
            {"name": "Python", "category": "programming_languages"},
            {"name": "React", "category": "frontend"},
        ]
        score, matched, missing = SkillMatcher.calculate_skill_score(
            ["Python", "React", "AWS"], skills
        )
        assert score > 60.0
        assert "Python" in matched
        assert "AWS" in missing


class TestProjectExtractor:
    def test_extract_projects(self) -> None:
        text = "My Project\nBuilt with React and Node\nTechnologies: React, Node.js"
        result = ProjectExtractor.extract(text)
        assert len(result) >= 1
        assert any("My Project" in p.get("name", "") for p in result)


class TestCertificationExtractor:
    def test_extract_certifications(self) -> None:
        text = "AWS Certified Solutions Architect\nCertified Kubernetes Administrator"
        result = CertificationExtractor.extract(text)
        assert len(result) >= 1
        names = [c.get("name", "") for c in result]
        assert any("AWS" in n for n in names)


class TestLanguageExtractor:
    def test_extract_languages(self) -> None:
        text = "English (Native)\nSpanish (Intermediate)"
        result = LanguageExtractor.extract(text)
        assert len(result) >= 2
        langs = [l.get("language") for l in result]
        assert "English" in langs
        assert "Spanish" in langs


class TestResumeAnalysis:
    def test_analysis_with_full_data(self) -> None:
        parsed = {
            "personal_info": {"name": "John"},
            "education": [{"degree": "BS"}],
            "experience": [{"title": "Engineer"}],
            "skills": [{"name": "Python"}],
            "projects": [{"name": "Project"}],
            "raw_text": "achieved improved developed launched team project metric",
        }
        analysis = ResumeAnalysisEngine.analyze(parsed)
        assert analysis["quality_score"] >= 50
        assert analysis["ats_score"] > 0
        assert len(analysis.get("missing_sections", [])) == 0

    def test_analysis_with_empty_data(self) -> None:
        parsed: dict = {
            "personal_info": {},
            "education": [],
            "experience": [],
            "skills": [],
            "projects": [],
            "raw_text": "",
        }
        analysis = ResumeAnalysisEngine.analyze(parsed)
        assert analysis["quality_score"] < 50
        assert len(analysis.get("missing_sections", [])) > 0

    def test_keyword_analysis(self) -> None:
        parsed = {
            "raw_text": "achieved improved launched delivered",
        }
        analysis = ResumeAnalysisEngine.analyze(parsed)
        ka = analysis.get("keyword_analysis", {})
        assert ka.get("matched_action_keywords", 0) >= 4


class TestResumeService:
    @pytest.mark.asyncio
    async def test_upload_txt_resume(self, session) -> None:
        db_session = session
        user_id = uuid.uuid4()
        profile = CandidateProfile(
            user_id=user_id,
            phone="+1555123456",
        )
        db_session.add(profile)
        await db_session.flush()
        await db_session.commit()

        service = ResumeService(db_session)
        content = SAMPLE_RESUME_TEXT.encode("utf-8")
        resume = await service.upload_resume(
            user_id=user_id,
            profile_id=profile.id,
            file_content=content,
            original_filename="resume.txt",
        )

        assert resume.original_filename == "resume.txt"
        assert resume.file_type == "txt"
        assert resume.status == ResumeStatus.UPLOADED

        resumes = await service.get_resumes(user_id)
        assert len(resumes) >= 1

    @pytest.mark.asyncio
    async def test_duplicate_detection(self, session) -> None:
        db_session = session
        user_id = uuid.uuid4()
        profile = CandidateProfile(
            user_id=user_id,
            phone="+1555123456",
        )
        db_session.add(profile)
        await db_session.flush()

        service = ResumeService(db_session)
        content = b"test content for duplicate"

        resume1 = await service.upload_resume(
            user_id=user_id,
            profile_id=profile.id,
            file_content=content,
            original_filename="test.txt",
        )
        assert resume1 is not None

        with pytest.raises(ValueError, match="duplicate"):
            await service.upload_resume(
                user_id=user_id,
                profile_id=profile.id,
                file_content=content,
                original_filename="test2.txt",
            )

    @pytest.mark.asyncio
    async def test_unsupported_file_type(self, session) -> None:
        db_session = session
        user_id = uuid.uuid4()
        profile = CandidateProfile(
            user_id=user_id,
            phone="+1555123456",
        )
        db_session.add(profile)
        await db_session.flush()

        service = ResumeService(db_session)
        with pytest.raises(ValueError, match="Unsupported file type"):
            await service.upload_resume(
                user_id=user_id,
                profile_id=profile.id,
                file_content=b"test",
                original_filename="resume.exe",
            )

    @pytest.mark.asyncio
    async def test_delete_resume(self, session) -> None:
        db_session = session
        user_id = uuid.uuid4()
        profile = CandidateProfile(
            user_id=user_id,
            phone="+1555123456",
        )
        db_session.add(profile)
        await db_session.flush()

        service = ResumeService(db_session)
        content = b"test content"
        resume = await service.upload_resume(
            user_id=user_id,
            profile_id=profile.id,
            file_content=content,
            original_filename="delete_test.txt",
        )

        deleted = await service.delete_resume(resume.id, user_id)
        assert deleted is True

        deleted_again = await service.delete_resume(resume.id, user_id)
        assert deleted_again is False

    @pytest.mark.asyncio
    async def test_resume_status(self, session) -> None:
        db_session = session
        user_id = uuid.uuid4()
        profile = CandidateProfile(
            user_id=user_id,
            phone="+1555123456",
        )
        db_session.add(profile)
        await db_session.flush()

        service = ResumeService(db_session)
        content = b"test content"
        resume = await service.upload_resume(
            user_id=user_id,
            profile_id=profile.id,
            file_content=content,
            original_filename="status_test.txt",
        )

        status = await service.get_resume_status(resume.id, user_id)
        assert status is not None
        assert status["status"] == "uploaded"
