"""Profile Agent (Phase 3) — reconcile perceived input into the candidate profile.

Honest, deterministic agent:
- unions skills from the existing candidate profile and lateral perception inputs
- canonicalizes through the shared skill dictionary / SkillGraph
- computes completeness with the platform's weighting semantics
- proposes only grounded recommendations (missing sections, transferable skills,
  unstated career intent)
- persists a snapshot (``Skill2JobProfileState``) so later phases and the UI can
  build on it without re-hydrating the recruiters' data
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.skill2job_models import Skill2JobPerception
from app.skill2job.adapters.candidate_adapter import CandidateAdapter
from app.skill2job.adapters.profile_state_adapter import PROFILE_STATE_VERSION, ProfileStateAdapter
from app.skill2job.profile.completeness import compute_completeness
from app.skill2job.profile.normalization import canonicalize_skill, merge_skill_sources
from app.skill2job.profile.schemas import (
    CorrectionItem,
    NormalizedSkillEntry,
    ProfileDossier,
    RecommendationItem,
    ReviewRequest,
    ReviewResult,
    SkillExpansionSuggestion,
)

logger = logging.getLogger(__name__)

ALLOWED_PROFILE_FIELDS = {"location", "current_role", "bio", "nationality"}
MAX_RECENT_PERCEPTIONS = 5


class ProfileAgent:
    def __init__(self, session: AsyncSession, candidate_adapter: CandidateAdapter) -> None:
        self._session = session
        self._candidate = candidate_adapter
        self._state_adapter = ProfileStateAdapter(session)

    # ─── Protocol: build_profile ──────────────────────────────────────────

    async def build_profile(self, state: dict) -> dict:
        user_id = state.get("user_id")
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        dossier = await self.build_dossier(user_id)
        return dossier.model_dump(mode="json")

    # ─── Dossier ──────────────────────────────────────────────────────────

    async def build_dossier(self, user_id: uuid.UUID) -> ProfileDossier:
        profile = await self._candidate.get_profile(user_id)
        try:
            intelligence = await self._candidate.get_intelligence(user_id)
        except Exception:
            intelligence = None
        sections = await self._candidate.profile_sections(user_id)

        skills_merged = await self._collect_skills(user_id)
        evidence = {s["name"]: s["sources"] for s in skills_merged}

        has_personal = bool(
            (profile.location or "").strip()
            or (profile.bio or "").strip()
            or (profile.current_role or "").strip()
        )
        completeness = compute_completeness(
            has_personal_info=has_personal,
            education_count=sections["education"],
            experience_count=sections["experience"],
            skill_count=len(skills_merged),
            projects_count=sections["projects"],
            certifications_count=sections["certifications"],
            languages_count=sections["languages"],
        )

        target_roles = await self._collect_target_roles(user_id)

        recommendations = self._build_recommendations(
            completeness=completeness,
            current_role=(profile.current_role or "").strip(),
            skill_count=len(skills_merged),
            target_roles=target_roles,
        )
        suggestions = self._build_suggestions(skills_merged)

        source_breakdown: dict[str, int] = {}
        for s in skills_merged:
            for src in s["sources"]:
                source_breakdown[src] = source_breakdown.get(src, 0) + 1

        experience_years = intelligence.total_experience_years if intelligence else None

        dossier = ProfileDossier(
            user_id=str(user_id),
            generated_at=datetime.now(timezone.utc),
            version=PROFILE_STATE_VERSION,
            profile=profile.model_dump(mode="json"),
            skills=[NormalizedSkillEntry(**s) for s in skills_merged],
            skill_count=len(skills_merged),
            education_count=sections["education"],
            experience_count=sections["experience"],
            experience_years=experience_years,
            target_roles=target_roles,
            completeness=completeness,
            recommendations=recommendations,
            suggestions=suggestions,
            source_breakdown=source_breakdown,
        )

        existing = await self._state_adapter.get(user_id)
        corrections = list(existing.corrections or []) if existing else []
        await self._state_adapter.upsert(
            user_id=user_id,
            dossier=dossier.model_dump(mode="json"),
            skill_evidence=evidence,
            completeness=completeness.model_dump(mode="json"),
            corrections=corrections,
        )
        return dossier

    async def get_dossier(self, user_id: uuid.UUID) -> dict | None:
        state = await self._state_adapter.get(user_id)
        if state is None or not state.normalized_profile:
            return None
        return state.normalized_profile

    # ─── Review / correction application ──────────────────────────────────

    async def apply_review(self, user_id: uuid.UUID, request: ReviewRequest) -> ReviewResult:
        applied: list[dict] = []
        for raw in request.skills_to_add:
            if not (raw or "").strip():
                continue
            applied.append(await self._candidate.add_skill_by_name(user_id, raw))

        corrections_applied: list[dict] = []
        profile_fields: dict[str, str] = {}
        for corr in request.corrections[:]:
            if corr.field in ALLOWED_PROFILE_FIELDS and corr.value:
                profile_fields[corr.field] = corr.value
                corrections_applied.append(
                    {"field": corr.field, "value": corr.value, "status": "applied"}
                )
            else:
                corrections_applied.append(
                    {"field": corr.field, "value": corr.value, "status": "stored"}
                )
        if profile_fields:
            await self._candidate.update_profile_fields(user_id, profile_fields)

        excluded = [s for s in request.skills_to_exclude if (s or "").strip()]

        existing = await self._state_adapter.get(user_id)
        previous = list(existing.corrections or []) if existing else []
        previous.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "applied": applied,
                "excluded": excluded,
                "corrections": corrections_applied,
            }
        )
        await self._state_adapter.upsert(
            user_id=user_id,
            dossier=(existing.normalized_profile or {}) if existing else {},
            skill_evidence=(existing.skill_evidence or {}) if existing else {},
            completeness=(existing.completeness or {}) if existing else {},
            corrections=previous,
        )
        return ReviewResult(
            applied_skills=applied,
            excluded_skills=excluded,
            corrections_applied=corrections_applied,
        )

    # ─── Internals ────────────────────────────────────────────────────────

    async def _collect_skills(self, user_id: uuid.UUID) -> list[dict]:
        entries: list[dict] = []
        sections = await self._candidate.profile_sections(user_id)
        for skill in sections["skills"]:
            raw = (skill.skill.name if skill.skill else "") or ""
            if not raw:
                continue
            canon = canonicalize_skill(raw)
            entries.append(
                {
                    "display": canon["display"],
                    "canonical": canon["canonical"],
                    "category": canon["category"],
                    "known": canon["known"],
                    "sources": ["candidate_profile"],
                    "inferred": False,
                }
            )

        perceptions = await self._recent_perceptions(user_id)
        for record in perceptions:
            result = record.result or {}
            source = f"perception:{record.input_type}"
            for skill in result.get("skills", []):
                raw = skill.get("name") or ""
                if not raw:
                    continue
                canon = canonicalize_skill(raw)
                entries.append(
                    {
                        "display": canon["display"],
                        "canonical": canon["canonical"],
                        "category": canon["category"],
                        "known": canon["known"],
                        "sources": [source],
                        "inferred": skill.get("inferred", False),
                    }
                )

        return merge_skill_sources(entries)

    async def _recent_perceptions(self, user_id: uuid.UUID) -> list[Skill2JobPerception]:
        result = await self._session.execute(
            select(Skill2JobPerception)
            .where(
                Skill2JobPerception.user_id == user_id,
                Skill2JobPerception.processing_status == "ok",
            )
            .order_by(Skill2JobPerception.created_at.desc())
            .limit(MAX_RECENT_PERCEPTIONS)
        )
        return list(result.scalars().all())

    async def _collect_target_roles(self, user_id: uuid.UUID) -> list[str]:
        roles: list[str] = []
        result = await self._session.execute(
            select(Skill2JobPerception)
            .where(
                Skill2JobPerception.user_id == user_id,
                Skill2JobPerception.processing_status == "ok",
            )
            .order_by(Skill2JobPerception.created_at.desc())
            .limit(MAX_RECENT_PERCEPTIONS)
        )
        for record in list(result.scalars().all()):
            for role in (record.result or {}).get("target_roles", []):
                if role not in roles:
                    roles.append(role)
        return roles

    @staticmethod
    def _build_recommendations(
        *,
        completeness,
        current_role: str,
        skill_count: int,
        target_roles: list[str],
    ) -> list[RecommendationItem]:
        recs: list[RecommendationItem] = []
        for section in completeness.missing_sections:
            priority = "high" if section in ("personal_info", "skills") else "medium"
            recs.append(
                RecommendationItem(
                    category="profile_section",
                    priority=priority,
                    title=f"Complete your {completeness_labels.get(section, section.replace('_', ' '))} section",
                    description=section_hints.get(
                        section,
                        f"Add your {section.replace('_', ' ')} to improve your profile.",
                    ),
                )
            )
        if not current_role:
            recs.append(
                RecommendationItem(
                    category="career",
                    priority="high",
                    title="Add your current role",
                    description="Your candidate profile has no current role; adding one helps job matching target the right opportunities.",
                )
            )
        if not target_roles:
            recs.append(
                RecommendationItem(
                    category="career",
                    priority="medium",
                    title="State a target role",
                    description="No target role has been perceived. Mention the role you're seeking in a resume or a quick career intent input.",
                )
            )
        if skill_count == 0:
            recs.append(
                RecommendationItem(
                    category="profile_section",
                    priority="high",
                    title="Add at least 3 skills",
                    description="Your profile has no recognizable skills. Upload a resume or add skills so matching can score career fits.",
                )
            )
        elif skill_count < 3:
            recs.append(
                RecommendationItem(
                    category="profile_section",
                    priority="medium",
                    title="Add a few more skills",
                    description=f"Your profile has {skill_count} skill(s); the platform considers 3+ a complete profile.",
                )
            )
        return recs

    @staticmethod
    def _build_suggestions(skills_merged: list[dict]) -> list[SkillExpansionSuggestion]:
        from app.services.screening.skill_graph import SkillGraph

        suggestions: list[SkillExpansionSuggestion] = []
        known = [s for s in skills_merged if s.get("known")]
        explored: set[str] = set()
        for skill in known:
            related = SkillGraph.get_related_skills(skill["name"])
            new_related = [
                r for r in related if r.lower() not in {s["name"].lower() for s in skills_merged}
            ]
            if not new_related or skill["name"].lower() in explored:
                continue
            explored.add(skill["name"].lower())
            suggestions.append(
                SkillExpansionSuggestion(
                    skill=new_related[0],
                    related_to=[skill["name"]],
                    reason=(
                        f"'{new_related[0]}' sits in the same transferable skill group as "
                        f"'{skill['name']}' in the shared skill graph."
                    ),
                )
            )
            if len(suggestions) >= 10:
                break
        return suggestions


completeness_labels = {
    "personal_info": "personal information",
    "education": "education",
    "experience": "experience",
    "skills": "skills",
    "projects": "projects",
    "certifications": "certifications",
    "languages": "languages",
}

section_hints = {
    "personal_info": "Location, bio or current role are missing from your profile.",
    "education": "Add your educational background to attract more career matches.",
    "experience": "List your work experience so matching can compute real experience signals.",
    "skills": "Add at least 3 skills to appear in recruiter searches.",
    "projects": "Adding projects showcases practical, demonstrable skill usage.",
    "certifications": "Certifications are low-cost, verifiable proof of skills.",
    "languages": "Languages expand the set of roles and locations you're eligible for.",
}