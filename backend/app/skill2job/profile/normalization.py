"""Skill normalization & canonicalization for the Profile Agent (Phase 3).

Delegates to the platform-shared skill dictionary (``SkillNormalizer``) and the
existing in-memory ``SkillGraph`` (synonym aliases and transferable groups).
Unknown words never become skills.
"""

from __future__ import annotations

from typing import Any


def canonicalize_skill(raw: str) -> dict[str, Any]:
    """Return {display, canonical, category, known}.

    ``canonical`` is set only when the name resolves in the shared dictionary or
    the SkillGraph; otherwise it stays ``None`` (not fabricated).
    """
    from app.services.candidate.resume_parser.skill_normalizer import SkillNormalizer
    from app.services.screening.skill_graph import SkillGraph

    raw = (raw or "").strip()
    if not raw:
        return {"display": "", "canonical": None, "category": None, "known": False}

    normalized = SkillNormalizer.normalize(raw)
    if normalized:
        return {
            "display": normalized.name,
            "canonical": normalized.name,
            "category": normalized.category,
            "known": True,
        }

    canonical = SkillGraph.find_canonical(raw)
    if canonical:
        return {
            "display": canonical,
            "canonical": canonical,
            "category": None,
            "known": True,
        }

    return {
        "display": raw,
        "canonical": None,
        "category": None,
        "known": False,
    }


def merge_skill_sources(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Dedupe skills by canonical/display name, unioning their sources.

    Each entry: {name, canonical, category, known, sources: list[str], inferred}.
    """
    merged: dict[str, dict[str, Any]] = {}
    for entry in entries:
        key = (entry.get("canonical") or entry.get("display") or "").strip().lower()
        if not key:
            continue
        existing = merged.get(key)
        if existing is None:
            merged[key] = {
                "name": entry.get("display") or entry.get("canonical"),
                "canonical": entry.get("canonical"),
                "category": entry.get("category"),
                "known": entry.get("known", False),
                "sources": list(entry.get("sources", [])),
                "inferred": entry.get("inferred", False),
            }
            continue
        if existing["canonical"] is None and entry.get("canonical"):
            existing["canonical"] = entry["canonical"]
        if existing["category"] is None and entry.get("category"):
            existing["category"] = entry["category"]
        existing["known"] = existing["known"] or entry.get("known", False)
        for src in entry.get("sources", []):
            if src not in existing["sources"]:
                existing["sources"].append(src)
    return list(merged.values())