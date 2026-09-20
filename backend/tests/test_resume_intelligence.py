"""Phase 1 tests: Resume Intelligence Engine.

Covers: intelligent section detection (synonyms/fuzzy/multi-line), structured
experience extraction, skill normalization & categories, projects, education,
certifications, achievement classification, source traceability, legacy
backward compatibility, and graceful degradation on garbage input.
"""

from pathlib import Path

import pytest

from app.services.candidate.resume_parser.date_utils import (
    compute_duration_months,
    format_duration,
    parse_date_range,
    parse_single_date,
)
from app.services.candidate.resume_parser.engine import ResumeIntelligenceEngine
from app.services.candidate.resume_parser.schemas import ResumeProfile
from app.services.candidate.resume_parser.section_detector import IntelligentSectionParser
from app.services.candidate.resume_parser.skill_normalizer import SkillNormalizer
from app.services.candidate.resume_parser.structured_extractors import (
    EducationMapper,
    ExperienceExtractorV2,
    ProjectExtractorV2,
)

SAMPLE_RESUME = """John Doe
john.doe@example.com | +1 555-123-4567

PROFESSIONAL BACKGROUND
Senior Software Engineer | Tech Corp Inc.
Jan 2020 - Present
• Led development of microservices architecture serving 1M+ users
• Improved deployment time by 60% with CI/CD pipeline
• Mentored team of junior engineers

Software Engineer | StartupXYZ
June 2017 - Dec 2019
• Developed React-based dashboards
• Wrote unit tests

ACADEMIC HISTORY
Master of Science in Computer Science
Stanford University
2015 - 2017
GPA: 3.9

TECHNICAL EXPERTISE
Python, JavaScript, React, FastAPI, PostgreSQL, Docker, Kubernetes, AWS,
Machine Learning, TensorFlow

CERTIFICATIONS
AWS Certified Solutions Architect — 2021
Certified Kubernetes Administrator (CKA), 2022

KEY PROJECTS
E-Commerce Platform
Technologies: React, Node.js, PostgreSQL
• Built checkout service handling 10k requests/day
• Wrote documentation
"""


@pytest.fixture(scope="module")
def parsed_sample(tmp_path_factory) -> tuple[ResumeProfile, dict]:
    tmp = tmp_path_factory.mktemp("resumes")
    file_path = tmp / "sample.txt"
    file_path.write_text(SAMPLE_RESUME, encoding="utf-8")
    return ResumeIntelligenceEngine.parse_file(file_path)


class TestDateUtils:
    def test_month_year_range(self):
        start, end, current = parse_date_range("Jan 2020 - Mar 2021")
        assert start.iso == "2020-01"
        assert end.iso == "2021-03"
        assert current is False

    def test_present_range(self):
        start, end, current = parse_date_range("June 2017 to Present")
        assert start.iso == "2017-06"
        assert end is None
        assert current is True

    def test_numeric_range(self):
        start, end, _ = parse_date_range("01/2020 - 06/2020")
        assert start.iso == "2020-01"
        assert end.iso == "2020-06"

    def test_year_only_is_uncertain(self):
        start, end, _ = parse_date_range("2018 to 2022")
        assert start.iso == "2018"
        assert start.uncertain is True
        assert end.iso == "2022"

    def test_unparseable_returns_none(self):
        start, end, current = parse_date_range("a long time ago")
        assert start is None and end is None and current is False

    def test_single_date(self):
        dv = parse_single_date("Graduated Sept 2019")
        assert dv.iso == "2019-09"

    def test_duration(self):
        from app.services.candidate.resume_parser.date_utils import DateValue

        months = compute_duration_months(
            DateValue(iso="2020-01"), DateValue(iso="2021-03"), False
        )
        assert months == 14
        assert format_duration(months) == "1 year 2 months"

    def test_duration_current_uses_today(self):
        from datetime import date

        from app.services.candidate.resume_parser.date_utils import DateValue

        months = compute_duration_months(DateValue(iso="2020-01"), None, True, today=date(2026, 8, 1))
        assert months == 79


class TestIntelligentSectionDetection:
    def test_standard_headers(self):
        sections, infos, warnings = IntelligentSectionParser.detect(
            "EXPERIENCE\nDid work\nEDUCATION\nStudied\nSKILLS\nPython"
        )
        assert sections["experience"] == "Did work"
        assert sections["education"] == "Studied"
        assert sections["skills"] == "Python"
        by_name = {i.section: i for i in infos}
        assert by_name["experience"].confidence >= 0.9

    def test_synonym_headers(self):
        text = (
            "PROFESSIONAL BACKGROUND\nWorked hard\n"
            "TECHNICAL EXPERTISE\nPython\n"
            "ACADEMIC HISTORY\nMIT\n"
            "KEY PROJECTS\nCool thing\n"
            "LICENSES & CERTIFICATIONS\nAWS Cert"
        )
        sections, _, _ = IntelligentSectionParser.detect(text)
        assert "Worked hard" in sections.get("experience", "")
        assert "Python" in sections.get("skills", "")
        assert "MIT" in sections.get("education", "")
        assert "Cool thing" in sections.get("projects", "")
        assert "AWS Cert" in sections.get("certifications", "")

    def test_fuzzy_header_typo(self):
        sections, infos, _ = IntelligentSectionParser.detect(
            "WORK EXPERAINCE\nBuilt things\nSKILLS\nGo"
        )
        assert "Built things" in sections.get("experience", "")
        exp_info = next(i for i in infos if i.section == "experience")
        assert exp_info.confidence >= 0.6

    def test_multiline_header(self):
        sections, _, _ = IntelligentSectionParser.detect("WORK\nEXPERIENCE\nDid stuff\nSKILLS\nRust")
        assert "Did stuff" in sections.get("experience", "")

    def test_unknown_heading_warning(self):
        _, _, warnings = IntelligentSectionParser.detect("ZORBLAX FROBNICATION\ncontent here")
        assert any("ZORBLAX" in w for w in warnings)


class TestExperienceExtraction:
    def test_structured_fields(self):
        section = (
            "Senior Software Engineer | Tech Corp Inc., Remote\n"
            "Jan 2020 - Present\n"
            "• Led development serving 1M+ users\n"
            "• Built REST APIs with FastAPI and PostgreSQL\n"
        )
        entries = ExperienceExtractorV2.extract(section)
        assert len(entries) == 1
        e = entries[0]
        assert e.job_title == "Senior Software Engineer"
        assert e.company == "Tech Corp Inc."
        assert e.start_date == "2020-01"
        assert e.end_date is None
        assert e.is_current is True
        assert e.duration_months is not None and e.duration_months > 0
        assert e.duration_label
        assert "FastAPI" in e.technologies or "PostgreSQL" in e.technologies

    def test_two_entries_split_without_blank_lines(self):
        section = (
            "Engineer | Acme Corp\nJan 2020 - Jan 2021\n• Did A\n"
            "Developer | Beta LLC\nFeb 2021 - Jun 2022\n• Did B\n"
        )
        entries = ExperienceExtractorV2.extract(section)
        assert len(entries) == 2
        assert entries[0].company == "Acme Corp"
        assert entries[1].company == "Beta LLC"
        assert entries[0].duration_months == 12

    def test_employment_type_and_location(self):
        section = "Data Analyst | Analytics Co | New York, NY (Contract)\n2021 - 2022\n• Analyzed data"
        entries = ExperienceExtractorV2.extract(section)
        assert len(entries) == 1
        e = entries[0]
        assert e.employment_type == "Contract"

    def test_year_only_dates_flagged_uncertain(self):
        section = "Engineer | Acme\n2018 - 2020\n• Worked"
        e = ExperienceExtractorV2.extract(section)[0]
        assert e.start_date == "2018"
        assert e.dates_uncertain is True


class TestAchievementClassification:
    def test_quantified_bullets_are_achievements(self):
        profile, _parsed = _parse_text(SAMPLE_RESUME)
        first_job = profile.experience[0]
        assert any("60%" in a for a in first_job.achievements)
        assert any("Mentored" in r for r in first_job.responsibilities)
        # description preserves everything
        assert len(first_job.description) == 3

    def test_project_achievements(self):
        profile, _parsed = _parse_text(SAMPLE_RESUME)
        project = profile.projects[0]
        assert any("10k" in a for a in project.achievements)
        assert any("documentation" in r for r in project.responsibilities)


class TestSkillNormalization:
    @pytest.mark.parametrize(
        "raw,expected_name,expected_category",
        [
            ("Python 3", "Python", "Programming Language"),
            ("python", "Python", "Programming Language"),
            ("Postgres", "PostgreSQL", "Database"),
            ("React.js", "React", "Framework"),
            ("Fast API", "FastAPI", "Framework"),
            ("k8s", "Kubernetes", "DevOps"),
            ("AWS", "AWS", "Cloud"),
            ("ml", "Machine Learning", "AI/ML"),
            ("CI/CD", "CI/CD", "DevOps"),
            ("Node.js", "Node.js", "Framework"),
        ],
    )
    def test_normalization(self, raw, expected_name, expected_category):
        skill = SkillNormalizer.normalize(raw)
        assert skill is not None
        assert skill.name == expected_name
        assert skill.category == expected_category
        assert skill.matched_on == raw

    def test_unknown_skill_returns_none(self):
        assert SkillNormalizer.normalize("Zorblax") is None
        assert SkillNormalizer.is_known_skill("Zorblax") is False

    def test_list_dedupe(self):
        skills = SkillNormalizer.normalize_list(["Python 3", "python", "Postgres"])
        names = [s.name for s in skills]
        assert names.count("Python") == 1
        assert "PostgreSQL" in names

    def test_profile_skills_categorized_and_traced(self):
        profile, _parsed = _parse_text(SAMPLE_RESUME)
        python = next(s for s in profile.skills if s.name == "Python")
        assert python.category == "Programming Language"
        assert python.source_section == "skills"
        inferred = [s for s in profile.skills if s.inferred]
        assert all(s.source_section for s in inferred)


class TestProjectExtraction:
    def test_projects_with_tech_line(self):
        profile, _parsed = _parse_text(SAMPLE_RESUME)
        assert len(profile.projects) >= 1
        p = profile.projects[0]
        assert p.name == "E-Commerce Platform"
        assert "React" in p.technologies
        assert "Node.js" in p.technologies
        assert "PostgreSQL" in p.technologies


class TestEducationAndCertifications:
    def test_education_normalized(self):
        profile, _parsed = _parse_text(SAMPLE_RESUME)
        ms = next(e for e in profile.education if e.degree and "Master" in e.degree)
        assert ms.institution and "Stanford" in ms.institution
        assert ms.field_of_study == "Computer Science"
        assert ms.start_date == "2015"
        assert ms.end_date == "2017"
        assert ms.gpa == "3.9"
        assert ms.source_section == "education"

    def test_certifications_with_iso_dates(self):
        profile, _parsed = _parse_text(SAMPLE_RESUME)
        aws = next(c for c in profile.certifications if "AWS" in c.name)
        assert aws.date_iso == "2021"
        cka = next(c for c in profile.certifications if "Kubernetes Administrator" in c.name)
        assert cka.date_iso == "2022"


class TestEngineEndToEnd:
    def test_profile_metadata_and_traceability(self, parsed_sample):
        profile, legacy = parsed_sample
        assert isinstance(profile, ResumeProfile)
        assert profile.metadata.parser_version.startswith("rie-")
        assert profile.metadata.processed_at.tzinfo is not None
        detected = {d.section for d in profile.metadata.detected_sections}
        assert {"experience", "education", "skills", "projects", "certifications"} <= detected
        # Source traceability present on entities.
        assert all(e.source_section == "experience" for e in profile.experience)
        assert profile.experience[0].source_text

    def test_profile_serializes_to_json(self, parsed_sample):
        profile, _legacy = parsed_sample
        assert ResumeProfile.model_validate_json(profile.model_dump_json())

    def test_summary_extracted(self):
        text = SAMPLE_RESUME.replace(
            "John Doe",
            "John Doe\nSUMMARY\nExperienced software engineer building scalable platforms.",
            1,
        )
        profile, _ = _parse_text(text)
        assert profile.summary and "scalable platforms" in profile.summary


class TestLegacyCompatibility:
    def test_legacy_dict_shape(self, parsed_sample):
        _profile, parsed = parsed_sample
        # Legacy top-level keys preserved.
        for key in (
            "raw_text", "language", "personal_info", "education", "experience",
            "skills", "projects", "certifications", "languages",
        ):
            assert key in parsed
        # Legacy experience keys preserved + enriched additively.
        exp = parsed["experience"][0]
        assert exp["title"] == "Senior Software Engineer"
        assert exp["company"] == "Tech Corp Inc."
        assert exp["start_date"] == "Jan 2020"
        assert exp["end_date"] is None
        assert isinstance(exp["description"], list)
        assert "job_title" in exp and "duration_months" in exp
        # Skills keep legacy keys + new fields.
        skill = parsed["skills"][0]
        assert "name" in skill and "category" in skill
        assert "display_name" in skill and "friendly_category" in skill
        # Education keeps legacy keys.
        edu = parsed["education"][0]
        assert "degree" in edu and "institution" in edu
        assert "Master" in (edu["degree"] or "")
        # Screening-style consumption still works.
        skill_names = {s["name"].lower() for s in parsed["skills"]}
        assert {"python", "react", "docker"} <= skill_names


def _parse_text(text: str) -> tuple[ResumeProfile, dict]:
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        path = f.name
    try:
        return ResumeIntelligenceEngine.parse_file(path)
    finally:
        Path(path).unlink(missing_ok=True)


class TestGracefulDegradation:
    def test_empty_sections_resume(self):
        profile, legacy = _parse_text("Jane Smith\njane@example.com")
        assert profile.personal_info is not None
        assert profile.experience == []
        assert profile.skills == []
        assert any("No experience section" in w for w in profile.metadata.warnings)
        assert legacy["experience"] == []

    def test_garbage_does_not_crash(self):
        profile, legacy = _parse_text(
            "!@#$%^&*() random noise \n more noise 12345 $$$\n broken dates: Feb 3021 - Hex 20XX"
        )
        assert profile.metadata.parser_version
        assert isinstance(legacy, dict)

    def test_empty_text_raises(self, tmp_path: Path):
        file_path = tmp_path / "empty.txt"
        file_path.write_text("", encoding="utf-8")
        with pytest.raises(ValueError):
            ResumeIntelligenceEngine.parse_file(file_path)


class TestRealWorldRegressions:
    """Issues surfaced by parsing a real fresher PDF resume (Aug 2026)."""

    def test_compound_certifications_heading(self):
        sections, infos, warnings = IntelligentSectionParser.detect(
            "Some project stuff\n"
            "CERTIFICATIONS AND WORK READINESS\n"
            "Done a Certification on PMP from Infosys Springboard"
        )
        assert "Infosys Springboard" in sections.get("certifications", "")
        assert "Some project stuff" not in sections.get("certifications", "")
        assert not any("CERTIFICATIONS" in w for w in warnings)

    def test_verb_start_project_has_no_fake_title(self):
        entries = ProjectExtractorV2.extract(
            "Developed an AI-powered desktop automation assistant using Python, Tkinter, SpeechRecognition\n"
            "• Built voice command handling with 95% accuracy\n"
            "Technologies: Python, Tkinter\n"
        )
        assert len(entries) == 1
        e = entries[0]
        assert e.name is None  # description sentence must NOT become the title
        assert any("AI-powered" in d for d in e.description)
        assert "Python" in e.technologies

    def test_titled_project_still_detected(self):
        entries = ProjectExtractorV2.extract(
            "CivicFix Platform\nBuilt issue reporting dashboard using React.js\n"
        )
        assert entries[0].name == "CivicFix Platform"

    def test_education_bullet_prefix_and_glued_dates(self):
        import re as _re

        from app.services.candidate.resume_parser.date_utils import parse_date_range

        entries = EducationMapper.extract(
            "• Sapthagiri NPS University Nov 2024 – Aug 2026\nGPA: 8.5"
        )
        assert len(entries) == 1
        e = entries[0]
        assert e.institution == "Sapthagiri NPS University"
        assert "2024" not in (e.institution or "")
        # Glued dates are still captured as normalized fields.
        start_dv, end_dv, _ = parse_date_range("Nov 2024 - Aug 2026")
        assert e.start_date == start_dv.iso == "2024-11"
        assert _re.match(r"^\d+\.\d+$", e.gpa or "")

    def test_combined_degree_institution_line(self):
        entries = EducationMapper.extract(
            "MCA - Sapthagiri NPS University Nov 2024 - Aug 2026"
        )
        assert len(entries) == 1
        e = entries[0]
        assert e.degree == "MCA"
        assert e.institution == "Sapthagiri NPS University"

    def test_phone_and_website_sanitized(self):
        import re as _re

        from app.services.candidate.resume_parser.personal_info_sanitizer import (
            sanitize_personal_info,
        )

        cleaned = sanitize_personal_info(
            {
                "email": "nagu22022002@gmail.com",
                "phone": "22022002",
                "alternate_phones": "+919353948700,1058257",
                "website": "gmail.com",
            }
        )
        assert cleaned["phone"] == "+919353948700"
        alts = cleaned.get("alternate_phones") or []
        assert all(len(_re.sub(r"\D", "", c)) >= 10 for c in alts)
        assert "website" not in cleaned

    def test_skill_display_name_not_double_lowered(self):
        profile, legacy = _parse_text(
            SAMPLE_RESUME.replace("Docker, Kubernetes", "Docker, Kubernetes, Tailwind CSS")
        )
        tailwind = next(s for s in legacy["skills"] if "tailwind" in s["name"])
        assert tailwind["display_name"] == "Tailwind CSS"


class TestServiceIntegration:
    @pytest.mark.asyncio
    async def test_process_resume_persists_profile_and_analysis(self, session) -> None:
        import uuid as uuid_mod

        from app.domain.models import CandidateProfile
        from app.services.candidate.resume import ResumeService

        user_id = uuid_mod.uuid4()
        profile = CandidateProfile(user_id=user_id, phone="+15550000000")
        session.add(profile)
        await session.flush()
        await session.commit()

        service = ResumeService(session)
        resume = await service.upload_resume(
            user_id=user_id,
            profile_id=profile.id,
            file_content=SAMPLE_RESUME.encode("utf-8"),
            original_filename="intel_resume.txt",
        )
        await service.process_resume(resume.id)
        await session.commit()

        detail = await service.get_resume_detail(resume.id, user_id)
        parsed = detail["parsed_data"]
        # Legacy-compatible persistence intact.
        assert parsed["experience"], "legacy experience list empty"
        assert parsed["skills"], "legacy skills list empty"
        # Structured Phase-1 payload persisted and complete.
        profile_json = parsed["resume_profile"]
        assert profile_json["metadata"]["parser_version"].startswith("rie-")
        assert profile_json["experience"][0]["company"] == "Tech Corp Inc."
        assert any(s["name"] == "Python" for s in profile_json["skills"])
        analysis = detail["analysis"]
        assert analysis is not None and analysis.quality_score >= 0

    @pytest.mark.asyncio
    async def test_delete_processed_resume_with_children(self, session) -> None:
        """Regression: deleting a PARSED resume previously failed with an
        IntegrityError because parsed_data/analysis lacked delete cascades."""
        import uuid as uuid_mod

        from app.domain.models import CandidateProfile
        from app.services.candidate.resume import ResumeService

        user_id = uuid_mod.uuid4()
        profile = CandidateProfile(user_id=user_id, phone="+15550000001")
        session.add(profile)
        await session.flush()
        await session.commit()

        service = ResumeService(session)
        resume = await service.upload_resume(
            user_id=user_id,
            profile_id=profile.id,
            file_content=SAMPLE_RESUME.encode("utf-8"),
            original_filename="delete_me.txt",
        )
        await service.process_resume(resume.id)
        await session.commit()

        # Dependent rows exist (this is what broke deletion before).
        assert await service.parsed_data_repo.get_by_resume(resume.id) is not None
        assert await service.analysis_repo.get_by_resume(resume.id) is not None

        deleted = await service.delete_resume(resume.id, user_id)
        await session.commit()
        assert deleted is True

        assert await service.resume_repo.get_by_user(resume.id, user_id) is None
        assert await service.parsed_data_repo.get_by_resume(resume.id) is None
        assert await service.analysis_repo.get_by_resume(resume.id) is None
