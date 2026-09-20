"""Change detection between a scenario's baseline and its proposed config.

Pure functions only — no session, no side effects. The builder renders the
result as a baseline-vs-scenario table with +/- movement indicators and
"skill moved Mandatory &rarr; Preferred" rows.

Comparison semantics:
- skill names are normalized through the platform SkillGraph, so an alias
  ("PostgreSQL" vs "postgres") is treated as the same skill;
- experience / education are compared as human-readable labels (structured
  ranges render e.g. "3–5 years", legacy job strings render verbatim);
- weights, threshold and shortlist_size compare numerically.
"""

from __future__ import annotations

import uuid

from app.domain.simulation_schemas import (
    SimulationChangesResponse,
    SimulationFieldChange,
    SimulationSkillMovement,
    SimulationSkillsChange,
)
from app.services.simulation.configuration_validator import (
    WEIGHT_DIMENSIONS,
    normalize_skill,
)

WEIGHT_LABELS: dict[str, str] = {
    "skills": "Skills",
    "experience": "Experience",
    "education": "Education",
    "projects": "Projects",
    "certifications": "Certifications",
    "location": "Location",
    "employment_type": "Employment type",
    "semantic": "Semantic match",
}

EDUCATION_LEVEL_LABELS: dict[str, str] = {
    "high_school": "High School",
    "associate": "Associate's",
    "bachelor": "Bachelor's",
    "master": "Master's",
    "doctorate": "Doctorate",
}

REQUIREMENT_LABELS: dict[str, str] = {
    "required": "Required",
    "preferred": "Preferred",
    "optional": "Optional",
}


def _number(value: object) -> float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _compare_number(baseline: object, scenario: object) -> str:
    base, scen = _number(baseline), _number(scenario)
    if base is None or scen is None:
        return "changed" if base != scen else "unchanged"
    if abs(base - scen) < 1e-9:
        return "unchanged"
    return "increased" if scen > base else "decreased"


def experience_label(requirements: dict) -> str:
    experience = requirements.get("experience")
    if isinstance(experience, dict):
        minimum = experience.get("minimum_years")
        maximum = experience.get("maximum_years")
        if minimum is not None and maximum is not None:
            return f"{minimum}–{maximum} years"
        if minimum is not None:
            return f"{minimum}+ years"
        if maximum is not None:
            return f"Up to {maximum} years"
    legacy = requirements.get("experience_required")
    return legacy or "—"


def education_label(requirements: dict) -> str:
    education = requirements.get("education")
    if isinstance(education, dict):
        level = education.get("level")
        requirement = education.get("requirement")
        if not level:
            return "Any level"
        level_text = EDUCATION_LEVEL_LABELS.get(level, level)
        if not requirement or requirement == "required":
            return level_text
        return f"{level_text} ({REQUIREMENT_LABELS.get(requirement, requirement)})"
    legacy = requirements.get("education_required")
    return legacy or "—"


def _skill_list(requirements: dict, key: str) -> list[str]:
    if not isinstance(requirements, dict):
        return []
    return [s for s in (requirements.get(key) or []) if isinstance(s, str)]


def _diff_skills(baseline: dict, scenario: dict) -> SimulationSkillsChange:
    base_mandatory = _skill_list(baseline.get("requirements"), "mandatory_skills")
    base_preferred = _skill_list(baseline.get("requirements"), "preferred_skills")
    scen_mandatory = _skill_list(scenario.get("requirements"), "mandatory_skills")
    scen_preferred = _skill_list(scenario.get("requirements"), "preferred_skills")

    def index(items: list[str]) -> dict[str, str]:
        return {normalize_skill(s): s for s in items}

    bm, bp = index(base_mandatory), index(base_preferred)
    sm, sp = index(scen_mandatory), index(scen_preferred)

    mandatory_added = [sm[k] for k in sm if k not in bm and k not in bp]
    mandatory_removed = [bm[k] for k in bm if k not in sm and k not in sp]
    preferred_added = [sp[k] for k in sp if k not in bp and k not in bm]
    preferred_removed = [bp[k] for k in bp if k not in sp and k not in sm]

    moved: list[SimulationSkillMovement] = [
        SimulationSkillMovement(skill=sp[k], from_list="mandatory", to_list="preferred")
        for k in sp
        if k in bm and k not in sm
    ]
    moved += [
        SimulationSkillMovement(skill=sm[k], from_list="preferred", to_list="mandatory")
        for k in sm
        if k in bp and k not in sp
    ]

    return SimulationSkillsChange(
        mandatory_added=mandatory_added,
        mandatory_removed=mandatory_removed,
        preferred_added=preferred_added,
        preferred_removed=preferred_removed,
        moved=moved,
    )


def _skill_delta_count(skills: SimulationSkillsChange) -> int:
    return (
        len(skills.mandatory_added)
        + len(skills.mandatory_removed)
        + len(skills.preferred_added)
        + len(skills.preferred_removed)
        + len(skills.moved)
    )


def compute_changes(
    simulation_id: uuid.UUID,
    config_version: int,
    baseline: dict,
    scenario: dict | None,
) -> SimulationChangesResponse:
    """Return a structured baseline-vs-scenario diff for display."""
    scenario = scenario or {}
    base_req = baseline.get("requirements") if isinstance(baseline, dict) else {}
    scen_req = scenario.get("requirements") if isinstance(scenario, dict) else {}

    fields: list[SimulationFieldChange] = []
    for dim in WEIGHT_DIMENSIONS:
        base_w = (baseline.get("scoring_weights") or {}).get(dim) if isinstance(baseline, dict) else None
        scen_w = (scenario.get("scoring_weights") or {}).get(dim) if isinstance(scenario, dict) else None
        fields.append(
            SimulationFieldChange(
                key=f"scoring_weights.{dim}",
                label=f"{WEIGHT_LABELS[dim]} weight",
                baseline=_number(base_w),
                scenario=_number(scen_w),
                change=_compare_number(base_w, scen_w),
            ),
        )

    fields.append(
        SimulationFieldChange(
            key="threshold",
            label="Pass threshold",
            baseline=(baseline or {}).get("threshold"),
            scenario=scenario.get("threshold"),
            change=_compare_number((baseline or {}).get("threshold"), scenario.get("threshold")),
        ),
    )
    fields.append(
        SimulationFieldChange(
            key="shortlist_size",
            label="Shortlist size",
            baseline=(baseline or {}).get("shortlist_size"),
            scenario=scenario.get("shortlist_size"),
            change=_compare_number((baseline or {}).get("shortlist_size"), scenario.get("shortlist_size")),
        ),
    )

    base_exp, scen_exp = experience_label(base_req), experience_label(scen_req)
    fields.append(
        SimulationFieldChange(
            key="requirements.experience",
            label="Experience",
            baseline=base_exp,
            scenario=scen_exp,
            change="changed" if base_exp != scen_exp else "unchanged",
        ),
    )
    base_edu, scen_edu = education_label(base_req), education_label(scen_req)
    fields.append(
        SimulationFieldChange(
            key="requirements.education",
            label="Education",
            baseline=base_edu,
            scenario=scen_edu,
            change="changed" if base_edu != scen_edu else "unchanged",
        ),
    )

    skills = _diff_skills(baseline or {}, scenario)

    changed_fields = [f.key for f in fields if f.change != "unchanged"]
    for list_key, items in (
        ("requirements.mandatory_skills", skills.mandatory_added + skills.mandatory_removed),
        ("requirements.preferred_skills", skills.preferred_added + skills.preferred_removed),
    ):
        if items:
            changed_fields.append(list_key)
    if skills.moved:
        changed_fields.append("requirements.skills_moved")

    total = len([f for f in fields if f.change != "unchanged"]) + _skill_delta_count(skills)

    return SimulationChangesResponse(
        simulation_id=simulation_id,
        config_version=config_version,
        total_changes=total,
        changed_fields=changed_fields,
        fields=fields,
        skills=skills,
    )