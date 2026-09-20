"""Phase 9: Learning Resource Intelligence Agent.

Exposes the consolidated curated catalog through a deterministic, auditable
API. Mapping from a skill to resources is resolved purely from the dataset
plus the existing SkillGraph — exact match first, then synonym / token
overlap, then a verified-programme fallback. Nothing is invented.
"""

from __future__ import annotations

import uuid

from app.services.screening.skill_graph import SkillGraph
from app.skill2job.learning.resources import RESOURCE_DATA_VERSION, _RESOURCE_CATALOG, sort_key
from app.skill2job.learning.schemas import (
    LearningResourcePublic,
    ResourceListResponse,
    ResourceMappingResponse,
    SkillResourceCandidate,
)

FALLBACK_RATIONALES = {
    "exact": "this skill is explicitly listed as covered by this resource.",
    "synonym": "matched through skill-graph synonyms or token overlap with this resource.",
    "fallback": "no specific curated resource covers this skill; shown as a starting-point programme with availability unverified.",
}

_FALLBACK_IDS = ("res_skill_india", "res_skill_india_hub")


def _to_public(resource: dict) -> LearningResourcePublic:
    return LearningResourcePublic(
        resource_id=resource["resource_id"],
        title=resource["title"],
        provider=resource["provider"],
        url=resource.get("url"),
        skills=list(resource.get("skills", [])),
        duration_hours=resource.get("duration_hours"),
        duration_weeks=resource.get("duration_weeks"),
        cost=resource.get("cost"),
        currency=resource.get("currency"),
        is_free=resource.get("is_free", False),
        pricing_type=resource.get("pricing_type", "unknown"),
        difficulty=resource.get("difficulty", "unknown"),
        format=resource.get("format", "unknown"),
        certificate=resource.get("certificate", False),
        skill_level=resource.get("skill_level", "unknown"),
        prerequisites=list(resource.get("prerequisites", [])),
        source_type=resource.get("source_type", "course"),
        skill_coverage=resource.get("skill_coverage", 0.5),
        last_verified_at=resource.get("last_verified_at"),
        verified=resource.get("verified", False),
        description=resource.get("description"),
    )


class LearningResourceAgent:
    def __init__(self, session=None) -> None:
        self._session = session

    # --- Public API ---

    def list_resources(
        self,
        skill_filter: str | None = None,
        free_only: bool = False,
        limit: int = 50,
        mode: str = "balanced",
    ) -> ResourceListResponse:
        pool = list(_RESOURCE_CATALOG)
        query = (skill_filter or "").strip().lower()
        if query:
            pool = [
                r
                for r in pool
                if query in r["title"].lower()
                or query in r["provider"].lower()
                or any(query in s.lower() for s in (r.get("skills") or []))
            ]
        if free_only:
            pool = [r for r in pool if r["is_free"]]
        pool.sort(key=lambda r: (sort_key(r, mode), r["title"].lower()))
        return ResourceListResponse(
            total=len(pool),
            resources=[_to_public(r) for r in pool[: max(limit, 1)]],
            version=RESOURCE_DATA_VERSION,
        )

    def resources_for_skill(
        self,
        skill: str,
        mode: str = "balanced",
        free_only: bool = False,
        limit: int = 5,
    ) -> ResourceMappingResponse:
        skill = (skill or "").strip()
        if not skill:
            return ResourceMappingResponse(skill=skill, mapped=False, version=RESOURCE_DATA_VERSION)

        direct = [
            r
            for r in _RESOURCE_CATALOG
            if self._covers(r, skill) and (not free_only or r["is_free"])
        ]
        if direct:
            return self._build(skill, direct, "exact", mode, limit)

        synonyms = [
            r
            for r in _RESOURCE_CATALOG
            if (not free_only or r["is_free"])
            and any(self._synonym_or_token(skill, rs) for rs in (r.get("skills") or []))
        ]
        if synonyms:
            return self._build(skill, synonyms, "synonym", mode, limit)

        return self._fallback(skill, mode, limit)

    # --- Internal helpers ---

    @staticmethod
    def _covers(resource: dict, skill: str) -> bool:
        return skill.lower() in {s.lower() for s in (resource.get("skills") or [])}

    @staticmethod
    def _synonym_or_token(input_skill: str, resource_skill: str) -> bool:
        if SkillGraph.are_synonyms(input_skill, resource_skill):
            return True
        input_tokens = set(SkillGraph.normalize(input_skill).split())
        resource_tokens = set(SkillGraph.normalize(resource_skill).split())
        if not input_tokens or not resource_tokens:
            return False
        return resource_tokens.issubset(input_tokens)

    def _build(
        self,
        skill: str,
        pool: list[dict],
        kind: str,
        mode: str,
        limit: int,
    ) -> ResourceMappingResponse:
        seen: set[str] = set()
        deduped: list[dict] = []
        for r in pool:
            if r["resource_id"] in seen:
                continue
            seen.add(r["resource_id"])
            deduped.append(r)
        deduped.sort(key=lambda r: (sort_key(r, mode), r["title"].lower()))
        candidates = [
            SkillResourceCandidate(
                resource=_to_public(r),
                mapping_kind=kind,
                coverage_pct=round((r.get("skill_coverage") or 0.0) * 100, 1),
                rationale=f"'{skill}': {FALLBACK_RATIONALES[kind]}",
            )
            for r in deduped[: max(limit, 1)]
        ]
        return ResourceMappingResponse(
            skill=skill, mapped=bool(candidates), resources=candidates, version=RESOURCE_DATA_VERSION
        )

    def _fallback(self, skill: str, mode: str, limit: int) -> ResourceMappingResponse:
        pool = [r for r in _RESOURCE_CATALOG if r["resource_id"] in _FALLBACK_IDS]
        pool.sort(key=lambda r: (sort_key(r, mode), r["title"].lower()))
        candidates = [
            SkillResourceCandidate(
                resource=_to_public(r),
                mapping_kind="fallback",
                coverage_pct=round((r.get("skill_coverage") or 0.0) * 100, 1),
                rationale=f"'{skill}': {FALLBACK_RATIONALES['fallback']}",
            )
            for r in pool[: max(limit, 1)]
        ]
        return ResourceMappingResponse(
            skill=skill, mapped=False, resources=candidates, version=RESOURCE_DATA_VERSION
        )


# Re-exported for parity with the engine name (kept importable for tests).
LEARNING_RESOURCE_VERSION = RESOURCE_DATA_VERSION