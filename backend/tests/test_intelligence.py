"""Tests for Candidate Intelligence, Profile Synchronization, and Resume Versioning."""

import uuid
from datetime import date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.enums import ResumeStatus, SkillCategory, SkillProficiency
from app.domain.models import (
    CandidateProfile,
    Certification,
    Education,
    Experience,
    Language,
    ParsedResumeData,
    Project,
    Resume,
    Skill,
    CandidateSkill,
    User,
)
from app.services.candidate.intelligence import CandidateIntelligenceService
from app.repositories.candidate.profile import CandidateProfileRepository
from app.repositories.candidate.education import EducationRepository
from app.repositories.candidate.experience import ExperienceRepository
from app.repositories.candidate.skill import CandidateSkillRepository, SkillRepository
from app.repositories.candidate.project import ProjectRepository
from app.repositories.candidate.certification import CertificationRepository
from app.repositories.candidate.language import LanguageRepository
from app.repositories.candidate.resume import ResumeRepository, ParsedResumeDataRepository


@pytest.fixture
def intel_service(session: AsyncSession) -> CandidateIntelligenceService:
    return CandidateIntelligenceService(
        profile_repo=CandidateProfileRepository(session),
        education_repo=EducationRepository(session),
        experience_repo=ExperienceRepository(session),
        candidate_skill_repo=CandidateSkillRepository(session),
        skill_repo=SkillRepository(session),
        project_repo=ProjectRepository(session),
        certification_repo=CertificationRepository(session),
        language_repo=LanguageRepository(session),
        resume_repo=ResumeRepository(session),
        parsed_repo=ParsedResumeDataRepository(session),
    )


async def _create_full_profile(session: AsyncSession, user_id: uuid.UUID) -> CandidateProfile:
    user = User(
        id=user_id,
        full_name="Test User",
        email="test@example.com",
        password_hash="hash",
    )
    session.add(user)
    profile = CandidateProfile(
        user_id=user_id,
        phone="+1234567890",
        location="New York",
        bio="Experienced developer",
        current_role="Senior Engineer",
        linkedin_url="https://linkedin.com/in/test",
    )
    session.add(profile)
    await session.flush()

    session.add(Education(profile_id=profile.id, institution="MIT", degree="Bachelor of Science in CS", start_date=date(2010, 9, 1), end_date=date(2014, 6, 1)))
    session.add(Education(profile_id=profile.id, institution="Stanford", degree="Master of Science in CS", start_date=date(2014, 9, 1), end_date=date(2016, 6, 1)))

    session.add(Experience(profile_id=profile.id, company="Google", job_title="SWE", start_date=date(2016, 7, 1), end_date=date(2020, 12, 31)))
    session.add(Experience(profile_id=profile.id, company="Meta", job_title="Senior SWE", start_date=date(2021, 1, 1), is_current=True))

    skill_py = Skill(name="Python", category=SkillCategory.PROGRAMMING_LANGUAGES)
    skill_js = Skill(name="JavaScript", category=SkillCategory.PROGRAMMING_LANGUAGES)
    skill_docker = Skill(name="Docker", category=SkillCategory.DEVOPS)
    session.add_all([skill_py, skill_js, skill_docker])
    await session.flush()

    session.add(CandidateSkill(profile_id=profile.id, skill_id=skill_py.id, proficiency=SkillProficiency.EXPERT, years_of_experience=8))
    session.add(CandidateSkill(profile_id=profile.id, skill_id=skill_js.id, proficiency=SkillProficiency.ADVANCED, years_of_experience=5))
    session.add(CandidateSkill(profile_id=profile.id, skill_id=skill_docker.id, proficiency=SkillProficiency.INTERMEDIATE, years_of_experience=3))

    session.add(Project(profile_id=profile.id, title="AI Platform", description="Built ML platform"))
    session.add(Project(profile_id=profile.id, title="Dashboard", description="React dashboard"))

    session.add(Certification(profile_id=profile.id, name="AWS Solutions Architect", organization="Amazon"))

    session.add(Language(profile_id=profile.id, language="English", reading="native", writing="native", speaking="native"))

    await session.flush()
    return profile


class TestCandidateIntelligence:
    @pytest.mark.asyncio
    async def test_get_intelligence_with_full_profile(self, session: AsyncSession, intel_service: CandidateIntelligenceService) -> None:
        user_id = uuid.uuid4()
        await _create_full_profile(session, user_id)

        result = await intel_service.get_intelligence(user_id)

        assert result.total_experience_years > 0
        assert result.total_experience_months > 0
        assert result.highest_qualification is not None
        assert "master" in result.education_level.lower()
        assert result.project_count == 2
        assert result.certification_count == 1
        assert result.language_count == 1
        assert result.profile_strength >= 60
        assert "programming_languages" in result.skills_by_category
        assert len(result.skill_summary) == 3

    @pytest.mark.asyncio
    async def test_get_intelligence_with_empty_profile(self, session: AsyncSession, intel_service: CandidateIntelligenceService) -> None:
        user_id = uuid.uuid4()
        user = User(id=user_id, full_name="Empty", email="empty@test.com", password_hash="hash")
        session.add(user)
        profile = CandidateProfile(user_id=user_id)
        session.add(profile)
        await session.flush()

        result = await intel_service.get_intelligence(user_id)

        assert result.total_experience_years == 0
        assert result.highest_qualification is None
        assert result.education_level == "not_specified"
        assert result.project_count == 0
        assert result.certification_count == 0
        assert result.language_count == 0
        assert result.profile_strength == 0
        assert len(result.missing_sections) > 0

    @pytest.mark.asyncio
    async def test_intelligence_recommendations(self, session: AsyncSession, intel_service: CandidateIntelligenceService) -> None:
        user_id = uuid.uuid4()
        user = User(id=user_id, full_name="Test", email="test2@test.com", password_hash="hash")
        session.add(user)
        profile = CandidateProfile(user_id=user_id)
        session.add(profile)
        await session.flush()

        result = await intel_service.get_intelligence(user_id)
        assert len(result.recommendations) > 0
        assert result.profile_strength == 0


class TestProfileSync:
    @pytest.mark.asyncio
    async def test_get_sync_diff_with_new_data(self, session: AsyncSession, intel_service: CandidateIntelligenceService) -> None:
        user_id = uuid.uuid4()
        profile = await _create_full_profile(session, user_id)

        resume = Resume(
            user_id=user_id,
            profile_id=profile.id,
            original_filename="resume.pdf",
            storage_path="/tmp/test.pdf",
            file_size=1000,
            file_type="pdf",
            mime_type="application/pdf",
            file_hash="abc123",
            status=ResumeStatus.PARSED,
            version=1,
            is_primary=True,
        )
        session.add(resume)
        await session.flush()

        parsed = ParsedResumeData(
            resume_id=resume.id,
            personal_info={"email": "newemail@test.com", "phone": "+9999999999"},
            education=[{"institution": "Harvard", "degree": "PhD"}],
            skills=[{"name": "Rust"}, {"name": "Kubernetes"}],
            projects=[{"name": "New Project", "description": "A new project"}],
            certifications=[{"name": "GCP Professional", "issuer": "Google"}],
            languages=[{"language": "French"}],
            raw_text="sample text",
        )
        session.add(parsed)
        await session.flush()

        result = await intel_service.get_sync_diff(resume.id, user_id)
        assert result is not None
        assert len(result.personal_info) > 0
        assert len(result.education) > 0
        assert len(result.skills) > 0
        assert len(result.projects) > 0
        assert len(result.certifications) > 0
        assert len(result.languages) > 0

    @pytest.mark.asyncio
    async def test_get_sync_diff_no_parsed_data(self, session: AsyncSession, intel_service: CandidateIntelligenceService) -> None:
        user_id = uuid.uuid4()
        user = User(id=user_id, full_name="Test", email="test3@test.com", password_hash="hash")
        session.add(user)
        profile = CandidateProfile(user_id=user_id)
        session.add(profile)
        await session.flush()
        resume = Resume(
            user_id=user_id,
            profile_id=profile.id,
            original_filename="test.pdf",
            storage_path="/tmp/test.pdf",
            file_size=500,
            file_type="pdf",
            mime_type="application/pdf",
            file_hash="def456",
            status=ResumeStatus.UPLOADED,
            version=1,
        )
        session.add(resume)
        await session.flush()

        result = await intel_service.get_sync_diff(resume.id, user_id)
        assert result is None


class TestResumeVersions:
    @pytest.mark.asyncio
    async def test_get_resume_versions(self, session: AsyncSession, intel_service: CandidateIntelligenceService) -> None:
        user_id = uuid.uuid4()
        user = User(id=user_id, full_name="Test", email="test4@test.com", password_hash="hash")
        session.add(user)
        profile = CandidateProfile(user_id=user_id)
        session.add(profile)
        await session.flush()

        for v in range(1, 4):
            session.add(Resume(
                user_id=user_id,
                profile_id=profile.id,
                original_filename=f"resume_v{v}.pdf",
                storage_path=f"/tmp/resume_v{v}.pdf",
                file_size=1000 * v,
                file_type="pdf",
                mime_type="application/pdf",
                file_hash=f"hash{v}",
                status=ResumeStatus.PARSED if v < 3 else ResumeStatus.UPLOADED,
                version=v,
                is_primary=(v == 3),
            ))
        await session.flush()

        versions = await intel_service.get_resume_versions(user_id)
        assert len(versions) == 3
        assert versions[0].version >= 1
        assert any(v.is_primary for v in versions)
        assert any(v.status == "parsed" for v in versions)
