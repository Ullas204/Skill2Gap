import asyncio
import uuid

from app.db.session import async_session_factory
from app.services.candidate.profile import ProfileService
from app.repositories.candidate.profile import CandidateProfileRepository
from app.repositories.candidate.education import EducationRepository
from app.repositories.candidate.experience import ExperienceRepository
from app.repositories.candidate.skill import CandidateSkillRepository, SkillRepository
from app.repositories.candidate.project import ProjectRepository
from app.repositories.candidate.certification import CertificationRepository
from app.repositories.candidate.language import LanguageRepository
from app.repositories.candidate.notification import NotificationRepository
from app.repositories.user import UserRepository

async def test():
    async with async_session_factory() as session:
        profile_repo = CandidateProfileRepository(session)
        svc = ProfileService(
            profile_repo=profile_repo,
            education_repo=EducationRepository(session),
            experience_repo=ExperienceRepository(session),
            candidate_skill_repo=CandidateSkillRepository(session),
            skill_repo=SkillRepository(session),
            project_repo=ProjectRepository(session),
            certification_repo=CertificationRepository(session),
            language_repo=LanguageRepository(session),
            notification_repo=NotificationRepository(session),
            user_repo=UserRepository(session),
        )
        result = await svc.get_dashboard(uuid.UUID("5017753f-1edb-4c18-9a02-e7e485268284"))
        print("Dashboard OK:", result)
        await session.commit()

asyncio.run(test())
