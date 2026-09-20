import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.candidate_schemas import CandidateProfileResponse
from app.domain.intelligence_schemas import CandidateIntelligence
from app.repositories.candidate.certification import CertificationRepository
from app.repositories.candidate.education import EducationRepository
from app.repositories.candidate.experience import ExperienceRepository
from app.repositories.candidate.language import LanguageRepository
from app.repositories.candidate.notification import NotificationRepository
from app.repositories.candidate.profile import CandidateProfileRepository
from app.repositories.candidate.project import ProjectRepository
from app.repositories.candidate.resume import ParsedResumeDataRepository, ResumeRepository
from app.repositories.candidate.skill import CandidateSkillRepository, SkillRepository
from app.repositories.user import UserRepository
from app.services.candidate.intelligence import CandidateIntelligenceService
from app.services.candidate.profile import ProfileService


class CandidateAdapter:
    """Thin adapter over the existing candidate domain.

    Skill2Job never re-implements profile loading or intelligence derivation; it
    delegates to the existing ProfileService / CandidateIntelligenceService.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._profile_service = ProfileService(
            profile_repo=CandidateProfileRepository(session),
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
        self._intel_service = CandidateIntelligenceService(
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

    async def profile_exists(self, user_id: uuid.UUID) -> bool:
        profile = await CandidateProfileRepository(self._session).get_by_user_id(user_id)
        return profile is not None

    async def get_profile(self, user_id: uuid.UUID) -> CandidateProfileResponse:
        return await self._profile_service.get_profile(user_id)

    async def get_intelligence(self, user_id: uuid.UUID) -> CandidateIntelligence:
        return await self._intel_service.get_intelligence(user_id)

    async def profile_sections(self, user_id: uuid.UUID) -> dict:
        """Counts for the candidate's existing profile sections (Phase 3)."""
        return {
            "education": len(await self._profile_service.list_education(user_id)),
            "experience": len(await self._profile_service.list_experiences(user_id)),
            "projects": len(await self._profile_service.list_projects(user_id)),
            "certifications": len(await self._profile_service.list_certifications(user_id)),
            "languages": len(await self._profile_service.list_languages(user_id)),
            "skills": await self._profile_service.list_skills(user_id),
        }

    async def add_skill_by_name(self, user_id: uuid.UUID, skill_name: str) -> dict:
        """Add a skill to the candidate profile by name (exact match only).

        Uses the existing ProfileService. Returns an honest result dict; unknown
        skills are never fabricated into the skill table.
        """
        matches = await self._profile_service.search_global_skills(skill_name)
        from app.domain.candidate_schemas import CandidateSkillCreate
        from app.domain.enums import SkillProficiency

        target = None
        for m in matches:
            if m["name"].strip().lower() == skill_name.strip().lower():
                target = m
                break
        if target is None:
            return {"applied": False, "reason": "Unknown in global skill dictionary", "name": skill_name}
        existing = await self._profile_service.list_skills(user_id)
        for s in existing:
            skill_label = (s.skill.name if s.skill else "") or ""
            if skill_label.lower() == target["name"].lower():
                return {"applied": False, "reason": "already on profile", "name": skill_name}
        await self._profile_service.add_skill(
            user_id,
            CandidateSkillCreate(skill_id=target["id"], proficiency=SkillProficiency.BEGINNER),
        )
        return {"applied": True, "reason": "added", "name": skill_name, "skill_id": target["id"]}

    async def update_profile_fields(self, user_id: uuid.UUID, fields: dict) -> None:
        from app.domain.candidate_schemas import CandidateProfileUpdate

        await self._profile_service.update_profile(
            user_id, CandidateProfileUpdate(**fields)
        )

    # ─── Interests (candidate profile intake) ────────────────────────────

    async def get_interests(self, user_id: uuid.UUID) -> list[str]:
        profile = await self.get_profile(user_id)
        return list(profile.interests or [])

    async def update_interests(self, user_id: uuid.UUID, interests: list[str]) -> list[str]:
        from app.domain.candidate_schemas import CandidateProfileUpdate

        cleaned = []
        for value in interests or []:
            label = str(value).strip()
            if label and label not in cleaned:
                cleaned.append(label)
        await self._profile_service.update_profile(
            user_id, CandidateProfileUpdate(interests=cleaned)
        )
        return cleaned

    # ─── Skill evidence tiers (Phase 2 semantic matching) ────────────────

    async def get_skill_evidence_map(self, user_id: uuid.UUID) -> dict[str, dict]:
        """Deterministic, provenance-grounded evidence tier per candidate skill.

        The four tiers match the product contract, weakest to strongest:
        - ``claimed``       : listed on the profile skill record only
        - ``supported``     : also extracted from a resume/document perception
        - ``demonstrated``  : appears inside project/experience technologies
        - ``verified``      : linked to a certification

        Only existing candidate data is used (profile skill summary, perception
        records, certifications). Missing skills map to ``none`` via the caller.
        """
        from sqlalchemy import select

        from app.domain.skill2job_models import Skill2JobPerception

        profile_record: dict[str, dict] = {}
        try:
            intelligence = await self.get_intelligence(user_id)
            for item in list(getattr(intelligence, "skill_summary", None) or []):
                if isinstance(item, dict):
                    name = item.get("name")
                    rec = item
                else:
                    name = getattr(item, "name", None)
                    rec = {}
                if not name:
                    continue
                key = str(name).strip().lower()
                profile_record[key] = {
                    "proficiency": rec.get("proficiency") if isinstance(rec, dict) else getattr(item, "proficiency", None),
                    "years": (
                        rec.get("years")
                        if isinstance(rec, dict)
                        else getattr(item, "years", None)
                    ),
                }
        except Exception:
            profile_record = {}

        per_count: dict[str, int] = {}
        tech_sources: dict[str, list[str]] = {}
        try:
            rows = (
                await self._session.execute(
                    select(Skill2JobPerception.result).where(
                        Skill2JobPerception.user_id == user_id
                    )
                )
            ).scalars().all()
            for res in rows:
                data = res if isinstance(res, dict) else dict(res or {})
                for item in data.get("skills", []) or []:
                    name = item.get("name") if isinstance(item, dict) else None
                    if name:
                        key = str(name).strip().lower()
                        per_count[key] = per_count.get(key, 0) + 1
                if isinstance(data.get("experience"), list):
                    for ent in data["experience"]:
                        if not isinstance(ent, dict):
                            continue
                        for t in ent.get("technologies", []) or []:
                            key = str(t).strip().lower()
                            if key:
                                tech_sources.setdefault(key, []).append("experience")
                if isinstance(data.get("projects"), list):
                    for ent in data["projects"]:
                        if not isinstance(ent, dict):
                            continue
                        for t in ent.get("technologies", []) or []:
                            key = str(t).strip().lower()
                            if key:
                                tech_sources.setdefault(key, []).append("projects")
                if isinstance(data.get("certifications"), list):
                    for ent in data["certifications"]:
                        name = ent.get("name") if isinstance(ent, dict) else None
                        if name:
                            key = str(name).strip().lower()
                            tech_sources.setdefault(key, []).append("certification")
        except Exception:
            per_count = {}
            tech_sources = {}

        evidence: dict[str, dict] = {}
        all_keys = set(profile_record.keys()) | set(per_count.keys()) | set(tech_sources.keys())
        for key in all_keys:
            state = "claimed"
            notes: list[str] = []
            rec = profile_record.get(key)
            if rec and (rec.get("proficiency") or rec.get("years") is not None):
                state = "supported"
                notes.append(
                    "profile skill record (proficiency: %s, years: %s)"
                    % (rec.get("proficiency") or "n/a", rec.get("years") if rec.get("years") is not None else 0)
                )
            elif rec:
                notes.append("listed on your profile")
            if per_count.get(key, 0) > 0:
                state = "supported"
                notes.append(
                    "found in %d resume perception(s)" % per_count[key]
                )
            srcs = tech_sources.get(key, [])
            if "experience" in srcs or "projects" in srcs:
                state = "demonstrated"
                notes.append("used in your project/experience technologies")
            if "certification" in srcs:
                state = "verified"
                notes.append("linked to a certification")
            evidence[key] = {"state": state, "notes": notes}
        return evidence