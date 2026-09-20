"""Pure, deterministic scoring adapter for Simulation executions (Phase 3).

Simulation is a READ-ONLY analytical layer over the live candidate pool. It
reuses the platform's single scoring source of truth — ``MatchingEngine`` — so
a hypothetical configuration is evaluated with exactly the same primitives the
live screening pipeline uses. It NEVER writes to live hiring records: every
function here is pure and derives its result from (candidate payload, frozen
configuration snapshot, job context).

A given (payload, config, job) tuple always produces the same score, which is
what makes simulation executions reproducible.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from app.services.screening.matching_engine import MatchingEngine


# Dimension name (as in ScreeningService.scores_dict) -> weight key
DIMENSION_KEYS: dict[str, str] = {
    "skill": "skills",
    "experience": "experience",
    "education": "education",
    "project": "projects",
    "certification": "certifications",
    "location": "location",
    "employment_type": "employment_type",
    "semantic": "semantic",
}

# Matches MatchingEngine.DEGREE_HIERARCHY so structured education levels align
# with the engine's degree ranking.
EDUCATION_LEVEL_RANK: dict[str, int] = {
    "high_school": 1,
    "associate": 3,
    "bachelor": 4,
    "master": 5,
    "doctorate": 6,
}


@dataclass
class CandidatePayload:
    """Everything the engine needs to know about one candidate, read-only.

    Built from CandidateProfile + related rows (skills/education/experience/
    projects/certifications) and the primary resume's parsed text. Missing
    profile data degrades gracefully to empty values so the candidate still
    appears in results with deterministic (low) scores.
    """

    candidate_id: uuid.UUID
    candidate_name: str
    skills: list[str] = field(default_factory=list)
    experience_years: float = 0.0
    degrees: list[str] = field(default_factory=list)
    project_count: int = 0
    project_technologies: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    location: str | None = None
    employment_preference: str | None = None
    resume_text: str = ""


@dataclass
class JobContext:
    """Stable job context used for location/employment/semantic dimensions.

    Mandatory skills are intentionally NOT part of the job context: they come
    from whichever configuration (baseline vs scenario) is being evaluated.
    """

    title: str
    location: str
    employment_type: str
    description: str = ""


@dataclass
class ScoredEvaluation:
    """Result of evaluating one config against one candidate.

    ``candidate_id`` is carried along so rankings can break ties deterministically
    without the engine depending on evaluation order.
    """

    candidate_id: uuid.UUID
    overall: int
    dimensions: dict[str, int]
    matched_skills: list[str]
    missing_required: list[str]
    missing_preferred: list[str]
    qualified: bool
    recommendation: str


# ─── Structured requirement helpers ───────────────────────────────────


def _max_degree_rank(degrees: list[str]) -> int:
    if not degrees:
        return 0
    return max(MatchingEngine._degree_level(d) for d in degrees)


def _experience_score_from_range(
    candidate_years: float,
    minimum: int | None,
    maximum: int | None,
) -> int:
    """Experience score for a structured [min, max] range.

    Mirrors the scale used by ``MatchingEngine.calculate_experience_match`` for
    the minimum bound, and applies a soft cap when the candidate exceeds the
    maximum bound (over-qualification).
    """
    if minimum is None and maximum is None:
        return 80
    score = 100
    if minimum is not None:
        if candidate_years >= minimum:
            score = 100
        else:
            ratio = candidate_years / minimum if minimum > 0 else 1.0
            if ratio >= 0.8:
                score = 85
            elif ratio >= 0.5:
                score = 60
            elif ratio >= 0.3:
                score = 40
            else:
                score = 20
    if maximum is not None and candidate_years > maximum:
        score = min(score, 50)
    return score


def evaluate_experience(candidate_years: float, requirements: dict) -> int:
    """Experience dimension score honoring the structured range when present."""
    experience = requirements.get("experience")
    if isinstance(experience, dict) and (
        experience.get("minimum_years") is not None
        or experience.get("maximum_years") is not None
    ):
        return _experience_score_from_range(
            candidate_years,
            experience.get("minimum_years"),
            experience.get("maximum_years"),
        )
    return MatchingEngine.calculate_experience_match(
        candidate_years, requirements.get("experience_required"),
    )


def evaluate_education(candidate_degrees: list[str], requirements: dict) -> int:
    """Education dimension score honoring the structured requirement when set.

    ``required`` is strict (engine scale), ``preferred`` is soft and
    ``optional`` is a no-op (neutral 80), consistent with the engine's no-
    constraint default.
    """
    education = requirements.get("education")
    if isinstance(education, dict) and education.get("level") in EDUCATION_LEVEL_RANK:
        required_level = EDUCATION_LEVEL_RANK[education["level"]]
        requirement = education.get("requirement", "required")
        if requirement == "optional":
            return 80
        candidate_max = _max_degree_rank(candidate_degrees)
        if candidate_max >= required_level:
            return 100
        diff = required_level - candidate_max
        if requirement == "preferred":
            return 65
        return 65 if diff == 1 else 30
    return MatchingEngine.calculate_education_match(
        candidate_degrees, requirements.get("education_required"),
    )


# ─── Core evaluation ──────────────────────────────────────────────────


def evaluate_configuration(
    payload: CandidatePayload,
    job: JobContext,
    config: dict,
) -> ScoredEvaluation:
    """Score one candidate under one configuration snapshot.

    This is the ONLY scoring entrypoint of the simulation engine. It is pure:
    no session, no writes, deterministic output.
    """
    weights = config.get("scoring_weights") or {}
    requirements = config.get("requirements") or {}
    threshold = int(config.get("threshold", 70))
    mandatory = list(requirements.get("mandatory_skills") or [])
    preferred = list(requirements.get("preferred_skills") or [])

    skill_score, matched, miss_req, miss_pref = MatchingEngine.calculate_skill_match(
        payload.skills, mandatory, preferred,
    )
    exp_score = evaluate_experience(payload.experience_years, requirements)
    edu_score = evaluate_education(payload.degrees, requirements)
    proj_score = MatchingEngine.calculate_project_match(
        payload.project_count, payload.project_technologies, mandatory,
    )
    cert_score = MatchingEngine.calculate_certification_match(payload.certifications, None)
    loc_score = MatchingEngine.calculate_location_match(payload.location, job.location)
    emp_score = MatchingEngine.calculate_employment_type_match(
        payload.employment_preference, job.employment_type,
    )
    jd_skills_text = " ".join(mandatory + preferred)
    jd_text = f"{job.title} {job.description} {jd_skills_text}".strip()
    semantic_score = MatchingEngine.calculate_semantic_similarity(payload.resume_text, jd_text)

    dimensions = {
        "skill": skill_score,
        "experience": exp_score,
        "education": edu_score,
        "project": proj_score,
        "certification": cert_score,
        "location": loc_score,
        "employment_type": emp_score,
        "semantic": semantic_score,
    }
    overall = MatchingEngine.calculate_overall_score(
        skill=skill_score,
        experience=exp_score,
        education=edu_score,
        project=proj_score,
        certification=cert_score,
        location=loc_score,
        employment_type=emp_score,
        semantic=semantic_score,
        weights=weights,
    )
    return ScoredEvaluation(
        candidate_id=payload.candidate_id,
        overall=overall,
        dimensions=dimensions,
        matched_skills=matched,
        missing_required=miss_req,
        missing_preferred=miss_pref,
        qualified=overall >= threshold,
        recommendation=MatchingEngine.determine_recommendation(overall),
    )


# ─── Ranking + explanation ────────────────────────────────────────────


def build_rankings(
    evaluations: list[ScoredEvaluation],
    shortlist_size: int,
) -> list[tuple[int, ScoredEvaluation, bool]]:
    """Rank evaluations by overall score desc (tiebreak: candidate id asc) and
    mark the top ``shortlist_size`` as shortlisted."""
    ordered = sorted(
        evaluations,
        key=lambda e: (-e.overall, str(e.candidate_id)),
    )
    return [
        (index, evaluation, index <= shortlist_size)
        for index, evaluation in enumerate(ordered, start=1)
    ]


def explain_score_change(
    base: ScoredEvaluation,
    sim: ScoredEvaluation,
    base_config: dict,
    sim_config: dict,
) -> str:
    """Short human-readable reason for why a candidate's outcome changed.

    Uses the per-dimension weighted contribution delta
    (sim_weight * sim_score - base_weight * base_score) to attribute the score
    movement to the dimensions that drove it. Falls back to status changes when
    the overall score did not move."
    """
    score_delta = sim.overall - base.overall
    base_weights = base_config.get("scoring_weights") or {}
    sim_weights = sim_config.get("scoring_weights") or {}

    contributions: dict[str, float] = {}
    for dim, weight_key in DIMENSION_KEYS.items():
        base_weight = base_weights.get(weight_key, 0.0)
        sim_weight = sim_weights.get(weight_key, 0.0)
        contributions[dim] = (
            sim_weight * sim.dimensions.get(dim, 0) - base_weight * base.dimensions.get(dim, 0)
        )

    parts: list[str] = []
    if base.qualified != sim.qualified:
        if sim.qualified:
            parts.append("now qualifies under the new threshold")
        else:
            parts.append("no longer qualifies under the new threshold")

    drivers = sorted(
        ((abs(v), k, v) for k, v in contributions.items()),
        key=lambda item: item[0],
        reverse=True,
    )
    meaningful = [d for d in drivers if d[0] >= 1.0][:2]
    if meaningful:
        fragments = []
        for prev, name, value in meaningful:
            sign = "+" if value >= 0 else ""
            fragments.append(f"{name.replace('_', ' ')} {sign}{round(value)}")
        parts.append("driven by " + " and ".join(fragments))

    if score_delta != 0:
        sign = "+" if score_delta > 0 else ""
        parts.append(f"overall {base.overall} -> {sim.overall} ({sign}{score_delta})")
    else:
        parts.append(f"overall score unchanged ({sim.overall})")

    return "; ".join(parts)[:500]