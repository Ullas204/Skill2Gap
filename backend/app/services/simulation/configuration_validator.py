"""Simulation configuration validation (Scenario Builder).

A dedicated, session-free validator so configuration rules live in one place:
the "what-if" sandbox can never persist an inconsistent configuration, and
promoting a scenario to `ready` (which triggers the validation gate) reports
the same structured errors the builder surfaces in the UI.

Rules validated here are cross-field / semantic rules that pydantic field
bounds cannot express alone:

- the eight scoring weights must total 100% (not merely be non-zero);
- skill lists must not contain duplicates or empty entries, and a skill cannot
  be both mandatory and preferred;
- a structured experience range must have ordered, non-negative bounds with at
  least one bound present;
- an education requirement must use a known platform level and requirement.

The validator accepts raw persisted JSON (``dict``) so stored configurations —
which round-trip through JSON, not through Pydantic on read — are re-checked
with the same rules used at write time.
"""

from __future__ import annotations

from app.domain.enums import (
    SimulationEducationLevel,
    SimulationEducationRequirement,
)
from app.domain.simulation_schemas import SimulationValidationIssue
from app.services.screening.skill_graph import SkillGraph

WEIGHT_DIMENSIONS: list[str] = [
    "skills",
    "experience",
    "education",
    "projects",
    "certifications",
    "location",
    "employment_type",
    "semantic",
]

WEIGHT_TOTAL = 1.0
WEIGHT_TOLERANCE = 1e-3

EDUCATION_LEVEL_VALUES = {level.value for level in SimulationEducationLevel}
EDUCATION_REQUIREMENT_VALUES = {req.value for req in SimulationEducationRequirement}

DEFAULT_THRESHOLD = 70
DEFAULT_SHORTLIST_SIZE = 10


def normalize_skill(skill: str) -> str:
    """Normalize a skill name for duplicate detection and diffing.

    Uses the platform's SkillGraph so aliases ("postgres" vs "PostgreSQL") and
    canonical names compare as the same skill.
    """
    cleaned = " ".join(skill.split()).strip().lower()
    if not cleaned:
        return ""
    canonical = SkillGraph.find_canonical(cleaned)
    return canonical if canonical else cleaned


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


class SimulationConfigurationValidator:
    """Collects structured validation issues for a simulation config."""

    @classmethod
    def validate(cls, config: dict | None) -> tuple[bool, list[SimulationValidationIssue]]:
        issues: list[SimulationValidationIssue] = []
        if config is None:
            issues.append(
                SimulationValidationIssue(
                    field="config",
                    message="No simulation configuration recorded. Configure the scenario before validating.",
                ),
            )
            return False, issues

        cls._validate_scoring(config, issues)
        cls._validate_threshold(config, issues)
        cls._validate_shortlist(config, issues)
        cls._validate_requirements(config, issues)
        return not issues, issues

    # ─── dimension validators ───────────────────────────────────────

    @classmethod
    def _validate_scoring(cls, config: dict, issues: list[SimulationValidationIssue]) -> None:
        weights = config.get("scoring_weights")
        if not isinstance(weights, dict):
            issues.append(
                SimulationValidationIssue(
                    field="scoring_weights",
                    message="Scoring weights are required.",
                ),
            )
            return

        total = 0.0
        for dim in WEIGHT_DIMENSIONS:
            value = weights.get(dim)
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                issues.append(
                    SimulationValidationIssue(
                        field=f"scoring_weights.{dim}",
                        message=f"Weight for {dim} must be a number between 0 and 1.",
                    ),
                )
                continue
            if value < 0 or value > 1:
                issues.append(
                    SimulationValidationIssue(
                        field=f"scoring_weights.{dim}",
                        message=f"Weight for {dim} must be between 0 and 1 (got {value}).",
                    ),
                )
            total += value

        if abs(total - WEIGHT_TOTAL) > WEIGHT_TOLERANCE:
            pct = round(total * 100, 1)
            issues.append(
                SimulationValidationIssue(
                    field="scoring_weights.total",
                    message=(
                        f"Scoring weights must total 100% (currently {pct}%). "
                        f"Adjust the weights so they sum to 100%."
                    ),
                ),
            )

    @classmethod
    def _validate_threshold(cls, config: dict, issues: list[SimulationValidationIssue]) -> None:
        threshold = config.get("threshold", DEFAULT_THRESHOLD)
        if not _is_int(threshold) or threshold < 0 or threshold > 100:
            issues.append(
                SimulationValidationIssue(
                    field="threshold",
                    message=f"Pass threshold must be a whole percentage between 0 and 100 (got {threshold!r}).",
                ),
            )

    @classmethod
    def _validate_shortlist(cls, config: dict, issues: list[SimulationValidationIssue]) -> None:
        shortlist = config.get("shortlist_size", DEFAULT_SHORTLIST_SIZE)
        if not _is_int(shortlist) or shortlist < 1 or shortlist > 500:
            issues.append(
                SimulationValidationIssue(
                    field="shortlist_size",
                    message=f"Shortlist size must be between 1 and 500 (got {shortlist!r}).",
                ),
            )

    @classmethod
    def _validate_requirements(cls, config: dict, issues: list[SimulationValidationIssue]) -> None:
        requirements = config.get("requirements")
        if not isinstance(requirements, dict):
            issues.append(
                SimulationValidationIssue(
                    field="requirements",
                    message="Requirements are required.",
                ),
            )
            return

        mandatory = requirements.get("mandatory_skills")
        preferred = requirements.get("preferred_skills")
        if not isinstance(mandatory, list):
            issues.append(
                SimulationValidationIssue(field="requirements.mandatory_skills", message="Mandatory skills must be a list."),
            )
            mandatory = []
        if not isinstance(preferred, list):
            issues.append(
                SimulationValidationIssue(field="requirements.preferred_skills", message="Preferred skills must be a list."),
            )
            preferred = []

        cls._validate_skill_list("requirements.mandatory_skills", mandatory, issues)
        cls._validate_skill_list("requirements.preferred_skills", preferred, issues)
        cls._validate_mandatory_preferred_overlap(mandatory, preferred, issues)
        cls._validate_experience(requirements, issues)
        cls._validate_education(requirements, issues)

    @staticmethod
    def _validate_skill_list(
        field: str, skills: list, issues: list[SimulationValidationIssue],
    ) -> None:
        seen: dict[str, str] = {}
        for skill in skills:
            if not isinstance(skill, str):
                issues.append(
                    SimulationValidationIssue(field=field, message=f"Each skill must be a string (got {skill!r})."),
                )
                continue
            normalized = normalize_skill(skill)
            if not normalized:
                issues.append(
                    SimulationValidationIssue(field=field, message="Skill names cannot be empty or whitespace-only."),
                )
                continue
            if normalized in seen:
                issues.append(
                    SimulationValidationIssue(
                        field=field,
                        message=f"Duplicated skill: \"{seen[normalized]}\" appears more than once.",
                    ),
                )
            seen[normalized] = skill.strip()

    @staticmethod
    def _validate_mandatory_preferred_overlap(
        mandatory: list, preferred: list, issues: list[SimulationValidationIssue],
    ) -> None:
        mandatory_norm = {normalize_skill(s) for s in mandatory if isinstance(s, str)}
        preferred_norm = {normalize_skill(s) for s in preferred if isinstance(s, str)}
        overlap = mandatory_norm & preferred_norm
        if overlap:
            names = "".join(sorted(overlap)) if False else ", ".join(sorted(overlap))
            issues.append(
                SimulationValidationIssue(
                    field="requirements",
                    message=f"A skill cannot be both mandatory and preferred: {names}.",
                ),
            )

    @classmethod
    def _validate_experience(cls, requirements: dict, issues: list[SimulationValidationIssue]) -> None:
        experience = requirements.get("experience")
        if experience is None:
            return
        if not isinstance(experience, dict):
            issues.append(
                SimulationValidationIssue(
                    field="requirements.experience",
                    message="Experience range must be an object with minimum_years / maximum_years.",
                ),
            )
            return

        minimum = experience.get("minimum_years")
        maximum = experience.get("maximum_years")
        if minimum is None and maximum is None:
            issues.append(
                SimulationValidationIssue(
                    field="requirements.experience",
                    message="Specify at least one of minimum or maximum years of experience.",
                ),
            )
            return

        for name, value in (("minimum_years", minimum), ("maximum_years", maximum)):
            if value is None:
                continue
            if not _is_int(value) or value < 0 or value > 50:
                issues.append(
                    SimulationValidationIssue(
                        field=f"requirements.experience.{name}",
                        message=f"Experience {name} must be a whole number between 0 and 50 (got {value!r}).",
                    ),
                )
        if (
            isinstance(minimum, int)
            and isinstance(maximum, int)
            and maximum < minimum
        ):
            issues.append(
                SimulationValidationIssue(
                    field="requirements.experience",
                    message=f"Maximum years ({maximum}) cannot be lower than minimum years ({minimum}).",
                ),
            )

    @classmethod
    def _validate_education(cls, requirements: dict, issues: list[SimulationValidationIssue]) -> None:
        education = requirements.get("education")
        if education is None:
            return
        if not isinstance(education, dict):
            issues.append(
                SimulationValidationIssue(
                    field="requirements.education",
                    message="Education requirement must be an object with level and requirement.",
                ),
            )
            return

        level = education.get("level")
        if level is not None and level not in EDUCATION_LEVEL_VALUES:
            issues.append(
                SimulationValidationIssue(
                    field="requirements.education.level",
                    message=f"Unknown education level: {level!r}. "
                    f"Use one of: {', '.join(sorted(EDUCATION_LEVEL_VALUES))}.",
                ),
            )
        requirement = education.get("requirement")
        if requirement is not None and requirement not in EDUCATION_REQUIREMENT_VALUES:
            issues.append(
                SimulationValidationIssue(
                    field="requirements.education.requirement",
                    message=f"Unknown education requirement: {requirement!r}. "
                    f"Use one of: {', '.join(sorted(EDUCATION_REQUIREMENT_VALUES))}.",
                ),
            )