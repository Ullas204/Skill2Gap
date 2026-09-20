import uuid
from datetime import date, datetime
from dateutil import parser as dateparser

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.domain.enums import Proficiency, SkillCategory, SkillProficiency
from app.domain.intelligence_schemas import (
    CandidateIntelligence,
    ResumeCompareResponse,
    ResumeVersionResponse,
    SkillSummaryItem,
    SyncActionRequest,
    SyncActionResult,
    SyncDiffItem,
    SyncDiffResponse,
)
from app.domain.models import (
    CandidateProfile,
    CandidateSkill,
    Certification,
    Education,
    Experience,
    Language,
    Project,
    Resume,
    Skill,
)
from app.repositories.candidate.certification import CertificationRepository
from app.repositories.candidate.education import EducationRepository
from app.repositories.candidate.experience import ExperienceRepository
from app.repositories.candidate.language import LanguageRepository
from app.repositories.candidate.profile import CandidateProfileRepository
from app.repositories.candidate.project import ProjectRepository
from app.repositories.candidate.resume import ParsedResumeDataRepository, ResumeRepository
from app.repositories.candidate.skill import CandidateSkillRepository, SkillRepository

logger = __import__("logging").getLogger(__name__)

DEGREE_ORDER = {
    "high school": 1,
    "ged": 1,
    "associate": 2,
    "associate degree": 2,
    "bachelor": 3,
    "bachelor's": 3,
    "bachelor of": 3,
    "b.tech": 3,
    "b.e.": 3,
    "b.sc": 3,
    "b.com": 3,
    "master": 4,
    "master's": 4,
    "master of": 4,
    "m.tech": 4,
    "m.e.": 4,
    "m.sc": 4,
    "mba": 4,
    "phd": 5,
    "ph.d": 5,
    "doctorate": 5,
    "doctor of": 5,
}


class CandidateIntelligenceService:
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
        resume_repo: ResumeRepository,
        parsed_repo: ParsedResumeDataRepository,
    ) -> None:
        self._profile_repo = profile_repo
        self._education_repo = education_repo
        self._experience_repo = experience_repo
        self._candidate_skill_repo = candidate_skill_repo
        self._skill_repo = skill_repo
        self._project_repo = project_repo
        self._certification_repo = certification_repo
        self._language_repo = language_repo
        self._resume_repo = resume_repo
        self._parsed_repo = parsed_repo
        self._session: AsyncSession = profile_repo._session

    async def get_intelligence(self, user_id: uuid.UUID) -> CandidateIntelligence:
        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            raise NotFoundError(detail="Profile not found")

        education = await self._education_repo.list_by_profile(profile.id)
        experience = await self._experience_repo.list_by_profile(profile.id)
        candidate_skills = await self._candidate_skill_repo.list_by_profile(profile.id)
        projects = await self._project_repo.list_by_profile(profile.id)
        certifications = await self._certification_repo.list_by_profile(profile.id)
        languages = await self._language_repo.list_by_profile(profile.id)

        total_exp_years, total_exp_months = self._compute_total_experience(experience)
        highest_qual, edu_level = self._compute_highest_qualification(education)

        skill_summary: list[SkillSummaryItem] = []
        skills_by_category: dict[str, list[str]] = {}
        for cs in candidate_skills:
            if cs.skill:
                item = SkillSummaryItem(
                    name=cs.skill.name,
                    category=cs.skill.category.value if hasattr(cs.skill.category, "value") else str(cs.skill.category),
                    proficiency=cs.proficiency.value if hasattr(cs.proficiency, "value") else str(cs.proficiency),
                    years=cs.years_of_experience,
                )
                skill_summary.append(item)
                cat = item.category
                if cat not in skills_by_category:
                    skills_by_category[cat] = []
                skills_by_category[cat].append(cs.skill.name)

        project_count = len(projects)
        certification_count = len(certifications)
        language_count = len(languages)

        profile_strength = self._compute_profile_strength(
            profile=profile,
            education_count=len(education),
            experience_count=len(experience),
            skill_count=len(candidate_skills),
            project_count=project_count,
            certification_count=certification_count,
        )

        missing_sections = self._get_missing_sections(
            profile=profile,
            education_count=len(education),
            experience_count=len(experience),
            skill_count=len(candidate_skills),
            project_count=project_count,
            certification_count=certification_count,
            language_count=language_count,
        )

        recommendations = self._generate_recommendations(missing_sections, profile_strength)

        return CandidateIntelligence(
            profile_id=profile.id,
            total_experience_years=total_exp_years,
            total_experience_months=total_exp_months,
            highest_qualification=highest_qual,
            education_level=edu_level,
            skill_summary=skill_summary,
            skills_by_category=skills_by_category,
            project_count=project_count,
            certification_count=certification_count,
            language_count=language_count,
            profile_strength=profile_strength,
            missing_sections=missing_sections,
            recommendations=recommendations,
        )

    def _compute_total_experience(self, experience: list) -> tuple[float, int]:
        total_days = 0
        for exp in experience:
            start = exp.start_date
            end = exp.end_date or date.today()
            if start and end:
                delta = (end - start).days
                total_days += max(delta, 0)
        years = round(total_days / 365.0, 1)
        months = int(total_days / 30.0)
        return years, months

    def _compute_highest_qualification(self, education: list) -> tuple[str | None, str]:
        if not education:
            return None, "not_specified"

        highest_level = 0
        highest_degree = None

        for edu in education:
            degree_lower = edu.degree.lower()
            for key, level in DEGREE_ORDER.items():
                if key in degree_lower:
                    if level > highest_level:
                        highest_level = level
                        highest_degree = edu.degree
                    break

        level_map = {0: "not_specified", 1: "high_school", 2: "associate", 3: "bachelor", 4: "master", 5: "doctorate"}
        edu_level = level_map.get(highest_level, "not_specified")
        return highest_degree, edu_level

    def _compute_profile_strength(
        self,
        profile: CandidateProfile,
        education_count: int,
        experience_count: int,
        skill_count: int,
        project_count: int,
        certification_count: int,
    ) -> int:
        score = 0
        if profile.phone:
            score += 10
        if profile.location:
            score += 10
        if profile.bio:
            score += 10
        if profile.current_role:
            score += 10
        if profile.linkedin_url or profile.github_url or profile.portfolio_url:
            score += 10
        if education_count > 0:
            score += 10
        if experience_count > 0:
            score += 10
        if skill_count >= 3:
            score += 10
        elif skill_count > 0:
            score += 5
        if project_count > 0:
            score += 10
        if certification_count > 0:
            score += 10
        return min(score, 100)

    def _get_missing_sections(
        self,
        profile: CandidateProfile,
        education_count: int,
        experience_count: int,
        skill_count: int,
        project_count: int,
        certification_count: int,
        language_count: int,
    ) -> list[str]:
        missing: list[str] = []
        if not profile.phone:
            missing.append("phone")
        if not profile.location:
            missing.append("location")
        if not profile.bio:
            missing.append("bio")
        if not profile.current_role:
            missing.append("current_role")
        if not (profile.linkedin_url or profile.github_url or profile.portfolio_url):
            missing.append("social_links")
        if education_count == 0:
            missing.append("education")
        if experience_count == 0:
            missing.append("experience")
        if skill_count == 0:
            missing.append("skills")
        if project_count == 0:
            missing.append("projects")
        if certification_count == 0:
            missing.append("certifications")
        if language_count == 0:
            missing.append("languages")
        return missing

    def _generate_recommendations(self, missing_sections: list[str], strength: int) -> list[str]:
        recs: list[str] = []
        section_labels = {
            "phone": "Add your phone number",
            "location": "Add your location",
            "bio": "Write a professional summary",
            "current_role": "Specify your current role",
            "social_links": "Add LinkedIn, GitHub, or portfolio links",
            "education": "Add your education details",
            "experience": "Add your work experience",
            "skills": "Add your skills",
            "projects": "Add your projects",
            "certifications": "Add your certifications",
            "languages": "Add your languages",
        }
        for section in missing_sections:
            if section in section_labels:
                recs.append(section_labels[section])

        if strength < 40:
            recs.append("Complete your profile to improve visibility to recruiters")
        elif strength < 70:
            recs.append("Your profile is getting stronger — keep adding more details")
        if not recs:
            recs.append("Your profile is complete! Keep it updated")

        return recs

    async def get_sync_diff(self, resume_id: uuid.UUID, user_id: uuid.UUID) -> SyncDiffResponse | None:
        resume = await self._resume_repo.get_by_user(resume_id, user_id)
        if not resume:
            return None

        parsed = await self._parsed_repo.get_by_resume(resume_id)
        if not parsed:
            return None

        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            return None

        education = await self._education_repo.list_by_profile(profile.id)
        experience = await self._experience_repo.list_by_profile(profile.id)
        candidate_skills = await self._candidate_skill_repo.list_by_profile(profile.id)
        projects = await self._project_repo.list_by_profile(profile.id)
        certifications = await self._certification_repo.list_by_profile(profile.id)
        languages = await self._language_repo.list_by_profile(profile.id)

        result = SyncDiffResponse(resume_id=resume_id)

        pi = parsed.personal_info or {}
        result.personal_info = [
            SyncDiffItem(section="personal_info", field="email", parsed_value=pi.get("email"), profile_value=profile.user.email if hasattr(profile, "user") else None),
            SyncDiffItem(section="personal_info", field="phone", parsed_value=pi.get("phone"), profile_value=profile.phone),
            SyncDiffItem(section="personal_info", field="location", parsed_value=pi.get("location"), profile_value=profile.location),
            SyncDiffItem(section="personal_info", field="linkedin", parsed_value=pi.get("linkedin_url") or pi.get("linkedin"), profile_value=profile.linkedin_url),
            SyncDiffItem(section="personal_info", field="github", parsed_value=pi.get("github_url") or pi.get("github"), profile_value=profile.github_url),
        ]
        result.personal_info = [d for d in result.personal_info if d.parsed_value or d.profile_value]

        parsed_edu = parsed.education or []
        profile_edu_map = {e.institution.lower(): e for e in education}
        for pe in parsed_edu:
            inst = (pe.get("institution") or "").lower()
            if inst and inst not in profile_edu_map:
                result.education.append(
                    SyncDiffItem(section="education", field="institution", parsed_value=pe.get("institution"), profile_value=None)
                )

        parsed_exp = parsed.experience or []
        profile_exp_map = {(e.company.lower(), e.job_title.lower()) for e in experience}
        for pe in parsed_exp:
            company = (pe.get("company") or "").lower()
            title = (pe.get("title") or "").lower()
            if company and (company, title) not in profile_exp_map:
                result.experience.append(
                    SyncDiffItem(section="experience", field="company", parsed_value=pe.get("company"), profile_value=None)
                )

        parsed_skills = parsed.skills or []
        profile_skill_names = {cs.skill.name.lower() for cs in candidate_skills if cs.skill}
        for ps in parsed_skills:
            name = (ps.get("name") or ps.get("skill") or "").lower()
            if name and name not in profile_skill_names:
                result.skills.append(
                    SyncDiffItem(section="skills", field="name", parsed_value=ps.get("name") or ps.get("skill"), profile_value=None)
                )

        parsed_projects = parsed.projects or []
        profile_project_names = {p.title.lower() for p in projects}
        for pp in parsed_projects:
            name = (pp.get("name") or pp.get("title") or "").lower()
            if name and name not in profile_project_names:
                result.projects.append(
                    SyncDiffItem(section="projects", field="name", parsed_value=pp.get("name") or pp.get("title"), profile_value=None)
                )

        parsed_certs = parsed.certifications or []
        profile_cert_names = {c.name.lower() for c in certifications}
        for pc in parsed_certs:
            name = (pc.get("name") or "").lower()
            if name and name not in profile_cert_names:
                result.certifications.append(
                    SyncDiffItem(section="certifications", field="name", parsed_value=pc.get("name"), profile_value=None)
                )

        parsed_langs = parsed.languages or []
        profile_lang_names = {l.language.lower() for l in languages}
        for pl in parsed_langs:
            name = (pl.get("language") or "").lower()
            if name and name not in profile_lang_names:
                result.languages.append(
                    SyncDiffItem(section="languages", field="language", parsed_value=pl.get("language"), profile_value=None)
                )

        return result

    async def get_resume_versions(self, user_id: uuid.UUID) -> list[ResumeVersionResponse]:
        resumes = await self._resume_repo.list_by_user(user_id)
        return [
            ResumeVersionResponse(
                id=r.id,
                version=r.version,
                original_filename=r.original_filename,
                file_size=r.file_size,
                file_type=r.file_type,
                status=r.status.value if hasattr(r.status, "value") else r.status,
                is_primary=r.is_primary,
                created_at=r.created_at,
            )
            for r in resumes
        ]

    async def accept_sync(self, body: SyncActionRequest, user_id: uuid.UUID) -> SyncActionResult:
        resume = await self._resume_repo.get_by_user(body.resume_id, user_id)
        if not resume:
            raise NotFoundError(detail="Resume not found")

        profile = await self._profile_repo.get_by_user_id(user_id)
        if not profile:
            raise NotFoundError(detail="Profile not found")

        parsed = await self._parsed_repo.get_by_resume(body.resume_id)
        if not parsed:
            raise NotFoundError(detail="Parsed data not found")

        applied = 0

        if body.section == "personal_info" and body.field:
            pi = parsed.personal_info or {}
            field_map = {
                "phone": ("phone", "phone"),
                "location": ("location", "location"),
                "linkedin": ("linkedin_url", "linkedin_url"),
                "github": ("github_url", "github_url"),
            }
            if body.field in field_map:
                parsed_key, profile_key = field_map[body.field]
                value = pi.get(parsed_key)
                if value:
                    await self._profile_repo.update(profile.id, **{profile_key: value})
                    applied += 1

        elif body.section == "education" and body.item_index is not None:
            items = parsed.education or []
            if 0 <= body.item_index < len(items):
                item = items[body.item_index]
                edu = Education(
                    profile_id=profile.id,
                    institution=item.get("institution") or "",
                    degree=item.get("degree") or "",
                    start_date=item.get("start_date"),
                    end_date=item.get("end_date"),
                )
                self._session.add(edu)
                applied += 1

        elif body.section == "experience" and body.item_index is not None:
            items = parsed.experience or []
            if 0 <= body.item_index < len(items):
                item = items[body.item_index]
                exp = Experience(
                    profile_id=profile.id,
                    company=item.get("company") or "",
                    job_title=item.get("title") or "",
                    start_date=item.get("start_date"),
                    end_date=item.get("end_date"),
                )
                self._session.add(exp)
                applied += 1

        elif body.section == "skills" and body.item_index is not None:
            items = parsed.skills or []
            if 0 <= body.item_index < len(items):
                item = items[body.item_index]
                name = item.get("name") or item.get("skill") or ""
                if name:
                    skill = await self._skill_repo.find_by_name(name)
                    if not skill:
                        skill = Skill(name=name, category=SkillCategory.TOOLS)
                        self._session.add(skill)
                        await self._session.flush()
                    if skill:
                        cs = CandidateSkill(
                            profile_id=profile.id,
                            skill_id=skill.id,
                            proficiency=SkillProficiency.INTERMEDIATE,
                        )
                        self._session.add(cs)
                        applied += 1

        elif body.section == "projects" and body.item_index is not None:
            items = parsed.projects or []
            if 0 <= body.item_index < len(items):
                item = items[body.item_index]
                proj = Project(
                    profile_id=profile.id,
                    title=item.get("name") or item.get("title") or "",
                    description=item.get("description"),
                    technologies=item.get("technologies"),
                )
                self._session.add(proj)
                applied += 1

        elif body.section == "certifications" and body.item_index is not None:
            items = parsed.certifications or []
            if 0 <= body.item_index < len(items):
                item = items[body.item_index]
                cert = Certification(
                    profile_id=profile.id,
                    name=item.get("name") or "",
                    organization=item.get("issuer") or item.get("organization") or "",
                    issue_date=item.get("issue_date"),
                    expiry_date=item.get("expiration_date"),
                )
                self._session.add(cert)
                applied += 1

        elif body.section == "languages" and body.item_index is not None:
            items = parsed.languages or []
            if 0 <= body.item_index < len(items):
                item = items[body.item_index]
                lang = Language(
                    profile_id=profile.id,
                    language=item.get("language") or "",
                    reading=Proficiency.INTERMEDIATE,
                    writing=Proficiency.INTERMEDIATE,
                    speaking=Proficiency.INTERMEDIATE,
                )
                self._session.add(lang)
                applied += 1

        if applied > 0:
            await self._session.flush()

        return SyncActionResult(message=f"Accepted {applied} item(s)", applied=applied)

    async def reject_sync(self, body: SyncActionRequest, user_id: uuid.UUID) -> SyncActionResult:
        resume = await self._resume_repo.get_by_user(body.resume_id, user_id)
        if not resume:
            raise NotFoundError(detail="Resume not found")

        parsed = await self._parsed_repo.get_by_resume(body.resume_id)
        if not parsed:
            raise NotFoundError(detail="Parsed data not found")

        removed = 0

        if body.section in ("education", "experience", "skills", "projects", "certifications", "languages") and body.item_index is not None:
            items = list(getattr(parsed, body.section, []) or [])
            if 0 <= body.item_index < len(items):
                items.pop(body.item_index)
                await self._parsed_repo.update(parsed.id, **{body.section: items})
                removed += 1

        elif body.section == "personal_info" and body.field:
            pi = dict(parsed.personal_info or {})
            field_keys = {"email": "email", "phone": "phone", "location": "location", "linkedin": "linkedin_url", "github": "github_url"}
            key = field_keys.get(body.field, body.field)
            if key in pi:
                del pi[key]
                await self._parsed_repo.update(parsed.id, personal_info=pi)
                removed += 1

        return SyncActionResult(message=f"Rejected {removed} item(s)", applied=removed)

    async def merge_sync(self, body: SyncActionRequest, user_id: uuid.UUID) -> SyncActionResult:
        return await self.accept_sync(body, user_id)

    async def compare_versions(self, version_id: uuid.UUID, user_id: uuid.UUID) -> ResumeCompareResponse | None:
        resume = await self._resume_repo.get_by_user(version_id, user_id)
        if not resume:
            return None

        all_resumes = await self._resume_repo.list_by_user(user_id)
        versions = [
            ResumeVersionResponse(
                id=r.id,
                version=r.version,
                original_filename=r.original_filename,
                file_size=r.file_size,
                file_type=r.file_type,
                status=r.status.value if hasattr(r.status, "value") else r.status,
                is_primary=r.is_primary,
                created_at=r.created_at,
            )
            for r in all_resumes
        ]

        current_parsed = await self._parsed_repo.get_by_resume(version_id)

        diffs: list[dict] = []

        primary = next((r for r in all_resumes if r.is_primary), None)
        if primary and primary.id != resume.id:
            primary_parsed = await self._parsed_repo.get_by_resume(primary.id)
            if current_parsed and primary_parsed:
                for section in ("education", "experience", "skills", "projects", "certifications", "languages"):
                    current_items = [str(item) for item in (getattr(current_parsed, section, None) or [])]
                    primary_items = [str(item) for item in (getattr(primary_parsed, section, None) or [])]
                    added = [c for c in current_items if c not in primary_items]
                    removed = [p for p in primary_items if p not in current_items]
                    if added or removed:
                        diffs.append({
                            "section": section,
                            "added": len(added),
                            "removed": len(removed),
                        })

        if not diffs and current_parsed:
            diffs.append({
                "section": "summary",
                "details": f"Resume v{resume.version} - {resume.original_filename}",
            })

        return ResumeCompareResponse(versions=versions, diffs=diffs)
