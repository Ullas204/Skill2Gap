import uuid

from sqlalchemy import func, select

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.domain.candidate_schemas import (
    CandidateProfileResponse,
    CandidateProfileUpdate,
    EducationCreate,
    EducationResponse,
    EducationUpdate,
    ExperienceCreate,
    ExperienceResponse,
    ExperienceUpdate,
    CandidateSkillCreate,
    CandidateSkillResponse,
    CandidateSkillUpdate,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    CertificationCreate,
    CertificationResponse,
    CertificationUpdate,
    LanguageCreate,
    LanguageResponse,
    LanguageUpdate,
    ProfileCompletionResponse,
)
from app.domain.models import CandidateProfile
from app.repositories.candidate.certification import CertificationRepository
from app.repositories.candidate.education import EducationRepository
from app.repositories.candidate.experience import ExperienceRepository
from app.repositories.candidate.language import LanguageRepository
from app.repositories.candidate.notification import NotificationRepository
from app.repositories.candidate.profile import CandidateProfileRepository
from app.repositories.candidate.project import ProjectRepository
from app.repositories.candidate.skill import CandidateSkillRepository, SkillRepository
from app.repositories.user import UserRepository

logger = get_logger(__name__)

SECTION_WEIGHTS = {
    "personal_info": 25, "education": 20, "experience": 20,
    "skills": 15, "projects": 10, "certifications": 5, "languages": 5,
}
PERSONAL_INFO_FIELDS = [
    "phone", "date_of_birth", "gender", "location", "nationality",
    "linkedin_url", "bio", "current_role", "interests",
]


class ProfileService:
    def __init__(
        self,
        profile_repo: CandidateProfileRepository,
        education_repo: EducationRepository,
        experience_repo: ExperienceRepository,
        candidate_skill_repo: CandidateSkillRepository,
        skill_repo: SkillRepository,
        project_repo: ProjectRepository,
        certification_repo: CertificationRepository,
        language_repo: LanguageRepository,
        notification_repo: NotificationRepository,
        user_repo: UserRepository,
    ) -> None:
        self._profile_repo = profile_repo
        self._education_repo = education_repo
        self._experience_repo = experience_repo
        self._candidate_skill_repo = candidate_skill_repo
        self._skill_repo = skill_repo
        self._project_repo = project_repo
        self._certification_repo = certification_repo
        self._language_repo = language_repo
        self._notification_repo = notification_repo
        self._user_repo = user_repo

    async def get_or_create_profile(self, user_id: uuid.UUID) -> CandidateProfile:
        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            profile = await self._profile_repo.create(user_id=user_id)
            await self._notification_repo.create_welcome_notification(user_id)
        return profile

    async def get_profile(self, user_id: uuid.UUID) -> CandidateProfileResponse:
        profile = await self.get_or_create_profile(user_id)
        return self._to_profile_response(profile)

    async def update_profile(self, user_id: uuid.UUID, data: CandidateProfileUpdate) -> CandidateProfileResponse:
        profile = await self.get_or_create_profile(user_id)
        kwargs = data.model_dump(exclude_unset=True)
        if kwargs:
            profile = await self._profile_repo.upsert(user_id=user_id, **kwargs)
            profile = await self._refresh_completion(profile)
        return self._to_profile_response(profile)

    async def get_dashboard(self, user_id: uuid.UUID) -> dict:
        profile = await self.get_or_create_profile(user_id)
        profile = await self._refresh_completion(profile)
        user = await self._user_repo.get(user_id)
        unread = await self._notification_repo.count_unread(user_id)
        notifications = await self._notification_repo.list_by_user(user_id)
        recent = [
            {"type": n.notification_type, "title": n.title, "message": n.message,
             "created_at": n.created_at.isoformat() if n.created_at else None}
            for n in notifications[:5]
        ]
        return {
            "profile": self._to_profile_response(profile),
            "full_name": user.full_name if user else "",
            "email": user.email if user else "",
            "total_resumes": 0,
            "total_notifications": len(notifications),
            "unread_notifications": unread,
            "recent_activity": recent,
        }

    async def get_completion(self, user_id: uuid.UUID) -> ProfileCompletionResponse:
        profile = await self.get_or_create_profile(user_id)
        sections = await self._evaluate_sections(profile)
        completion = sum(SECTION_WEIGHTS[s] for s, filled in sections.items() if filled)
        if completion != profile.profile_completion:
            await self._profile_repo.update(profile.id, profile_completion=completion)
        missing = [s.replace("_", " ").title() for s, filled in sections.items() if not filled]
        recs = {
            "personal_info": "Complete your personal information to improve visibility.",
            "education": "Add your educational background to attract recruiters.",
            "experience": "List your work experience to showcase your career.",
            "skills": "Add at least 3 skills to appear in searches.",
        }
        recommendations = [recs.get(s.lower().replace(" ", "_"), f"Add {s.lower()} to enhance your profile.") for s in missing]
        return ProfileCompletionResponse(
            completion_percentage=completion,
            sections=sections,
            missing_sections=missing,
            recommendations=recommendations,
        )

    async def upload_avatar(self, user_id: uuid.UUID, avatar_url: str) -> CandidateProfileResponse:
        profile = await self.get_or_create_profile(user_id)
        profile = await self._profile_repo.upsert(user_id=user_id, avatar_url=avatar_url)
        await self._notification_repo.create(
            user_id=user_id, title="Avatar Updated",
            message="Your profile picture has been updated successfully.",
            notification_type="avatar_changed",
        )
        return self._to_profile_response(profile)

    async def remove_avatar(self, user_id: uuid.UUID) -> CandidateProfileResponse:
        profile = await self.get_or_create_profile(user_id)
        profile = await self._profile_repo.upsert(user_id=user_id, avatar_url=None)
        return self._to_profile_response(profile)

    # --- Education ---
    async def list_education(self, user_id: uuid.UUID) -> list[EducationResponse]:
        profile = await self.get_or_create_profile(user_id)
        records = await self._education_repo.list_by_profile(profile.id)
        return [EducationResponse.model_validate(r) for r in records]

    async def create_education(self, user_id: uuid.UUID, data: EducationCreate) -> EducationResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._education_repo.create(profile_id=profile.id, **data.model_dump())
        await self._profile_repo.update(profile.id, updated_at=__import__("datetime").datetime.now())
        return EducationResponse.model_validate(record)

    async def update_education(self, user_id: uuid.UUID, edu_id: uuid.UUID, data: EducationUpdate) -> EducationResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._education_repo.get(edu_id)
        if not record or record.profile_id != profile.id:
            raise NotFoundError(detail="Education record not found")
        kwargs = data.model_dump(exclude_unset=True)
        record = await self._education_repo.update(edu_id, **kwargs)
        return EducationResponse.model_validate(record)

    async def delete_education(self, user_id: uuid.UUID, edu_id: uuid.UUID) -> None:
        profile = await self.get_or_create_profile(user_id)
        record = await self._education_repo.get(edu_id)
        if not record or record.profile_id != profile.id:
            raise NotFoundError(detail="Education record not found")
        await self._education_repo.delete(edu_id)

    # --- Experience ---
    async def list_experiences(self, user_id: uuid.UUID) -> list[ExperienceResponse]:
        profile = await self.get_or_create_profile(user_id)
        records = await self._experience_repo.list_by_profile(profile.id)
        return [ExperienceResponse.model_validate(r) for r in records]

    async def create_experience(self, user_id: uuid.UUID, data: ExperienceCreate) -> ExperienceResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._experience_repo.create(profile_id=profile.id, **data.model_dump())
        return ExperienceResponse.model_validate(record)

    async def update_experience(self, user_id: uuid.UUID, exp_id: uuid.UUID, data: ExperienceUpdate) -> ExperienceResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._experience_repo.get(exp_id)
        if not record or record.profile_id != profile.id:
            raise NotFoundError(detail="Experience record not found")
        kwargs = data.model_dump(exclude_unset=True)
        record = await self._experience_repo.update(exp_id, **kwargs)
        return ExperienceResponse.model_validate(record)

    async def delete_experience(self, user_id: uuid.UUID, exp_id: uuid.UUID) -> None:
        profile = await self.get_or_create_profile(user_id)
        record = await self._experience_repo.get(exp_id)
        if not record or record.profile_id != profile.id:
            raise NotFoundError(detail="Experience record not found")
        await self._experience_repo.delete(exp_id)

    # --- Skills ---
    async def list_skills(self, user_id: uuid.UUID) -> list[CandidateSkillResponse]:
        profile = await self.get_or_create_profile(user_id)
        records = await self._candidate_skill_repo.list_by_profile(profile.id)
        return [CandidateSkillResponse.model_validate(r) for r in records]

    async def add_skill(self, user_id: uuid.UUID, data: CandidateSkillCreate) -> CandidateSkillResponse:
        profile = await self.get_or_create_profile(user_id)
        skill = await self._skill_repo.get(data.skill_id)
        if not skill:
            raise NotFoundError(detail="Skill not found")
        existing = await self._candidate_skill_repo.find_one(profile_id=profile.id, skill_id=data.skill_id)
        if existing:
            record = await self._candidate_skill_repo.update(
                (profile.id, data.skill_id),
                proficiency=data.proficiency.value,
                years_of_experience=data.years_of_experience,
            )
        else:
            record = await self._candidate_skill_repo.create(
                profile_id=profile.id, skill_id=data.skill_id,
                proficiency=data.proficiency.value,
                years_of_experience=data.years_of_experience,
            )
        return CandidateSkillResponse.model_validate(record)

    async def update_skill(self, user_id: uuid.UUID, skill_id: int, data: CandidateSkillUpdate) -> CandidateSkillResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._candidate_skill_repo.find_one(profile_id=profile.id, skill_id=skill_id)
        if not record:
            raise NotFoundError(detail="Skill not found on profile")
        kwargs = data.model_dump(exclude_unset=True)
        if kwargs.get("proficiency"):
            kwargs["proficiency"] = kwargs["proficiency"].value if hasattr(kwargs["proficiency"], "value") else kwargs["proficiency"]
        record = await self._candidate_skill_repo.update((profile.id, skill_id), **kwargs)
        return CandidateSkillResponse.model_validate(record)

    async def remove_skill(self, user_id: uuid.UUID, skill_id: int) -> None:
        profile = await self.get_or_create_profile(user_id)
        record = await self._candidate_skill_repo.find_one(profile_id=profile.id, skill_id=skill_id)
        if not record:
            raise NotFoundError(detail="Skill not found on profile")
        await self._candidate_skill_repo.delete((profile.id, skill_id))

    async def search_global_skills(self, query: str) -> list[dict]:
        skills = await self._skill_repo.search(query)
        return [{"id": s.id, "name": s.name, "category": s.category} for s in skills]

    # --- Projects ---
    async def list_projects(self, user_id: uuid.UUID) -> list[ProjectResponse]:
        profile = await self.get_or_create_profile(user_id)
        records = await self._project_repo.list_by_profile(profile.id)
        return [ProjectResponse.model_validate(r) for r in records]

    async def create_project(self, user_id: uuid.UUID, data: ProjectCreate) -> ProjectResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._project_repo.create(profile_id=profile.id, **data.model_dump())
        return ProjectResponse.model_validate(record)

    async def update_project(self, user_id: uuid.UUID, proj_id: uuid.UUID, data: ProjectUpdate) -> ProjectResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._project_repo.get(proj_id)
        if not record or record.profile_id != profile.id:
            raise NotFoundError(detail="Project not found")
        kwargs = data.model_dump(exclude_unset=True)
        record = await self._project_repo.update(proj_id, **kwargs)
        return ProjectResponse.model_validate(record)

    async def delete_project(self, user_id: uuid.UUID, proj_id: uuid.UUID) -> None:
        profile = await self.get_or_create_profile(user_id)
        record = await self._project_repo.get(proj_id)
        if not record or record.profile_id != profile.id:
            raise NotFoundError(detail="Project not found")
        await self._project_repo.delete(proj_id)

    # --- Certifications ---
    async def list_certifications(self, user_id: uuid.UUID) -> list[CertificationResponse]:
        profile = await self.get_or_create_profile(user_id)
        records = await self._certification_repo.list_by_profile(profile.id)
        return [CertificationResponse.model_validate(r) for r in records]

    async def create_certification(self, user_id: uuid.UUID, data: CertificationCreate) -> CertificationResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._certification_repo.create(profile_id=profile.id, **data.model_dump())
        return CertificationResponse.model_validate(record)

    async def update_certification(self, user_id: uuid.UUID, cert_id: uuid.UUID, data: CertificationUpdate) -> CertificationResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._certification_repo.get(cert_id)
        if not record or record.profile_id != profile.id:
            raise NotFoundError(detail="Certification not found")
        kwargs = data.model_dump(exclude_unset=True)
        record = await self._certification_repo.update(cert_id, **kwargs)
        return CertificationResponse.model_validate(record)

    async def delete_certification(self, user_id: uuid.UUID, cert_id: uuid.UUID) -> None:
        profile = await self.get_or_create_profile(user_id)
        record = await self._certification_repo.get(cert_id)
        if not record or record.profile_id != profile.id:
            raise NotFoundError(detail="Certification not found")
        await self._certification_repo.delete(cert_id)

    # --- Languages ---
    async def list_languages(self, user_id: uuid.UUID) -> list[LanguageResponse]:
        profile = await self.get_or_create_profile(user_id)
        records = await self._language_repo.list_by_profile(profile.id)
        return [LanguageResponse.model_validate(r) for r in records]

    async def create_language(self, user_id: uuid.UUID, data: LanguageCreate) -> LanguageResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._language_repo.create(profile_id=profile.id, **data.model_dump())
        return LanguageResponse.model_validate(record)

    async def update_language(self, user_id: uuid.UUID, lang_id: uuid.UUID, data: LanguageUpdate) -> LanguageResponse:
        profile = await self.get_or_create_profile(user_id)
        record = await self._language_repo.get(lang_id)
        if not record or record.profile_id != profile.id:
            raise NotFoundError(detail="Language not found")
        kwargs = data.model_dump(exclude_unset=True)
        record = await self._language_repo.update(lang_id, **kwargs)
        return LanguageResponse.model_validate(record)

    async def delete_language(self, user_id: uuid.UUID, lang_id: uuid.UUID) -> None:
        profile = await self.get_or_create_profile(user_id)
        record = await self._language_repo.get(lang_id)
        if not record or record.profile_id != profile.id:
            raise NotFoundError(detail="Language not found")
        await self._language_repo.delete(lang_id)

    # --- Internal ---
    async def _refresh_completion(self, profile: CandidateProfile) -> CandidateProfile:
        sections = await self._evaluate_sections(profile)
        completion = sum(SECTION_WEIGHTS[s] for s, filled in sections.items() if filled)
        if completion != profile.profile_completion:
            return await self._profile_repo.update(profile.id, profile_completion=completion) or profile
        return profile

    async def _evaluate_sections(self, profile: CandidateProfile) -> dict[str, bool]:
        from app.domain.models import CandidateSkill, Certification, Education, Experience, Language, Project

        tables: dict[str, type] = {
            "education": Education,
            "experience": Experience,
            "skills": CandidateSkill,
            "projects": Project,
            "certifications": Certification,
            "languages": Language,
        }
        counts: dict[str, int] = {}
        session = self._profile_repo._session
        for key, model in tables.items():
            stmt = select(func.count()).select_from(model).where(model.profile_id == profile.id)
            result = await session.execute(stmt)
            counts[key] = result.scalar() or 0
        return {
            "personal_info": any(getattr(profile, f, None) for f in PERSONAL_INFO_FIELDS),
            "education": counts["education"] > 0,
            "experience": counts["experience"] > 0,
            "skills": counts["skills"] >= 3,
            "projects": counts["projects"] > 0,
            "certifications": counts["certifications"] > 0,
            "languages": counts["languages"] > 0,
        }

    @staticmethod
    def _to_profile_response(profile: CandidateProfile) -> CandidateProfileResponse:
        return CandidateProfileResponse.model_validate(profile)
