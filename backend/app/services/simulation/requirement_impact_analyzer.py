"""RequirementImpactAnalyzer — Phase 5 What-If Requirement Impact Analysis.

Consumes persisted Phase 3 results (SimulationResult, SimulationExecution)
and configuration snapshots to decompose ranking impact by individual
requirement changes.

Architecture:
    Phase 3: Candidate Pool -> Baseline Evaluation -> Simulation Evaluation
             -> Persist Candidate Results (with dimension scores)
    Phase 5: Persisted Candidate Results + Config Snapshots -> Requirement
             Impact Analyzer -> Requirement Impact Metrics -> Frontend Dashboard

This service is READ-ONLY with respect to production hiring data.
It never modifies JobDescription, CandidateRanking, Candidate, or Resume rows.

All calculations are deterministic and derived from actual simulation results.
"""

from __future__ import annotations

import statistics
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.requirement_impact_schemas import (
    CandidateRequirementImpactDetail,
    CandidateRequirementImpactDetailResponse,
    CandidateRequirementImpactListResponse,
    ChangedRequirementStatus,
    RequirementChangeDetail,
    RequirementChangeSummary,
    RequirementImpactListResponse,
    RequirementImpactResponse,
    RequirementImpactSummary,
)
from app.domain.simulation_models import (
    SimulationExecution,
    SimulationResult,
    SimulationScenario,
)
from app.repositories.simulation import SimulationRepository
from app.repositories.simulation_execution import (
    SimulationExecutionRepository,
    SimulationResultRepository,
)
from app.services.screening.matching_engine import MatchingEngine
from app.services.simulation.evaluation import (
    EDUCATION_LEVEL_RANK,
    _experience_score_from_range,
    _max_degree_rank,
)
from app.services.simulation.configuration_validator import normalize_skill

logger = get_logger(__name__)

# ─── Impact Category Thresholds ────────────────────────────────────

LOW_THRESHOLD = 5
MODERATE_THRESHOLD = 20


def _impact_category(affected: int) -> str:
    """Classify requirement impact by magnitude (neutral, not evaluative)."""
    if affected == 0:
        return "NO_CANDIDATE_IMPACT"
    if affected <= LOW_THRESHOLD:
        return "LOW_CANDIDATE_IMPACT"
    if affected <= MODERATE_THRESHOLD:
        return "MODERATE_CANDIDATE_IMPACT"
    return "HIGH_CANDIDATE_IMPACT"


def _safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    if denominator == 0:
        return default
    return numerator / denominator


# ─── Config Diff Helpers ───────────────────────────────────────────


def _skill_list(config: dict, key: str) -> list[str]:
    """Extract a skill list from a config dict, normalized."""
    requirements = config.get("requirements") or {}
    raw = requirements.get(key) or []
    return [normalize_skill(s) for s in raw if isinstance(s, str)]


def _identify_skill_changes(baseline: dict, simulation: dict) -> list[RequirementChangeDetail]:
    """Identify skill requirement changes between baseline and simulation."""
    base_mandatory = {normalize_skill(s) for s in (baseline.get("requirements") or {}).get("mandatory_skills") or []}
    base_preferred = {normalize_skill(s) for s in (baseline.get("requirements") or {}).get("preferred_skills") or []}
    sim_mandatory = {normalize_skill(s) for s in (simulation.get("requirements") or {}).get("mandatory_skills") or []}
    sim_preferred = {normalize_skill(s) for s in (simulation.get("requirements") or {}).get("preferred_skills") or []}

    # Build display name maps (normalized -> original)
    base_mandatory_names = {normalize_skill(s): s for s in (baseline.get("requirements") or {}).get("mandatory_skills") or [] if isinstance(s, str)}
    base_preferred_names = {normalize_skill(s): s for s in (baseline.get("requirements") or {}).get("preferred_skills") or [] if isinstance(s, str)}
    sim_mandatory_names = {normalize_skill(s): s for s in (simulation.get("requirements") or {}).get("mandatory_skills") or [] if isinstance(s, str)}
    sim_preferred_names = {normalize_skill(s): s for s in (simulation.get("requirements") or {}).get("preferred_skills") or [] if isinstance(s, str)}

    changes: list[RequirementChangeDetail] = []

    # Added to mandatory (not in baseline mandatory or preferred)
    for skill in sim_mandatory:
        if skill not in base_mandatory and skill not in base_preferred:
            name = sim_mandatory_names.get(skill, skill)
            changes.append(RequirementChangeDetail(
                requirement_type="skill",
                requirement_name=name,
                change_type="added",
                baseline_value="not required",
                simulation_value="mandatory",
            ))

    # Removed from mandatory (in baseline but not in simulation)
    for skill in base_mandatory:
        if skill not in sim_mandatory and skill not in sim_preferred:
            name = base_mandatory_names.get(skill, skill)
            changes.append(RequirementChangeDetail(
                requirement_type="skill",
                requirement_name=name,
                change_type="removed",
                baseline_value="mandatory",
                simulation_value="not required",
            ))

    # Promoted from preferred to mandatory
    for skill in sim_mandatory:
        if skill in base_preferred and skill not in base_mandatory:
            name = sim_mandatory_names.get(skill, skill)
            changes.append(RequirementChangeDetail(
                requirement_type="skill",
                requirement_name=name,
                change_type="promoted",
                baseline_value="preferred",
                simulation_value="mandatory",
            ))

    # Demoted from mandatory to preferred
    for skill in sim_preferred:
        if skill in base_mandatory and skill not in base_preferred:
            name = sim_preferred_names.get(skill, skill)
            changes.append(RequirementChangeDetail(
                requirement_type="skill",
                requirement_name=name,
                change_type="demoted",
                baseline_value="mandatory",
                simulation_value="preferred",
            ))

    # Added to preferred (not in baseline mandatory or preferred)
    for skill in sim_preferred:
        if skill not in base_mandatory and skill not in base_preferred:
            name = sim_preferred_names.get(skill, skill)
            # Only add if not already captured as added to mandatory
            if not any(c.requirement_name.lower() == name.lower() and c.change_type == "added" for c in changes):
                changes.append(RequirementChangeDetail(
                    requirement_type="skill",
                    requirement_name=name,
                    change_type="added",
                    baseline_value="not required",
                    simulation_value="preferred",
                ))

    # Removed from preferred
    for skill in base_preferred:
        if skill not in sim_mandatory and skill not in sim_preferred:
            name = base_preferred_names.get(skill, skill)
            # Only add if not already captured as removed from mandatory
            if not any(c.requirement_name.lower() == name.lower() and c.change_type == "removed" for c in changes):
                changes.append(RequirementChangeDetail(
                    requirement_type="skill",
                    requirement_name=name,
                    change_type="removed",
                    baseline_value="preferred",
                    simulation_value="not required",
                ))

    return changes


def _identify_experience_change(baseline: dict, simulation: dict) -> RequirementChangeDetail | None:
    """Identify experience requirement changes."""
    base_exp = (baseline.get("requirements") or {}).get("experience")
    sim_exp = (simulation.get("requirements") or {}).get("experience")

    base_label = _experience_label(base_exp)
    sim_label = _experience_label(sim_exp)

    if base_label == sim_label:
        return None

    return RequirementChangeDetail(
        requirement_type="experience",
        requirement_name="experience",
        change_type="modified",
        baseline_value=base_label,
        simulation_value=sim_label,
    )


def _identify_education_change(baseline: dict, simulation: dict) -> RequirementChangeDetail | None:
    """Identify education requirement changes."""
    base_edu = (baseline.get("requirements") or {}).get("education")
    sim_edu = (simulation.get("requirements") or {}).get("education")

    base_label = _education_label(base_edu)
    sim_label = _education_label(sim_edu)

    if base_label == sim_label:
        return None

    return RequirementChangeDetail(
        requirement_type="education",
        requirement_name="education",
        change_type="modified",
        baseline_value=base_label,
        simulation_value=sim_label,
    )


def _experience_label(exp: dict | None) -> str:
    """Human-readable experience label from a requirements dict."""
    if not exp or not isinstance(exp, dict):
        return "not specified"
    minimum = exp.get("minimum_years")
    maximum = exp.get("maximum_years")
    if minimum is not None and maximum is not None:
        return f"{minimum}-{maximum} years"
    if minimum is not None:
        return f"{minimum}+ years"
    if maximum is not None:
        return f"up to {maximum} years"
    return "not specified"


def _education_label(edu: dict | None) -> str:
    """Human-readable education label from a requirements dict."""
    if not edu or not isinstance(edu, dict):
        return "not specified"
    level = edu.get("level")
    requirement = edu.get("requirement", "required")
    if not level:
        return "any level"
    level_map = {
        "high_school": "High School",
        "associate": "Associate's",
        "bachelor": "Bachelor's",
        "master": "Master's",
        "doctorate": "Doctorate",
    }
    level_text = level_map.get(level, level)
    if requirement == "required":
        return level_text
    if requirement == "preferred":
        return f"{level_text} (preferred)"
    return f"{level_text} (optional)"


# ─── Satisfaction Check Helpers ────────────────────────────────────


def _check_skill_satisfied(matched_skills: list[str], missing_required: list[str], missing_preferred: list[str], skill_name: str, is_mandatory: bool) -> bool:
    """Check if a candidate satisfies a skill requirement using persisted satisfaction data."""
    skill_lower = normalize_skill(skill_name)
    # Check if the skill is in matched skills
    for s in matched_skills:
        if normalize_skill(s) == skill_lower:
            return True
    # Check if the skill is missing
    if is_mandatory:
        for s in missing_required:
            if normalize_skill(s) == skill_lower:
                return False
    else:
        for s in missing_preferred:
            if normalize_skill(s) == skill_lower:
                return False
    # If not in matched and not in missing, check if the skill was even required
    # If the skill wasn't in any required/preferred list in this config, it's not applicable
    return True  # Skill not in this config's requirements = satisfied (not applicable)


def _check_experience_satisfied(candidate_years: float, experience_config: dict | None) -> bool:
    """Check if a candidate satisfies an experience requirement."""
    if not experience_config or not isinstance(experience_config, dict):
        return True  # No requirement = satisfied
    minimum = experience_config.get("minimum_years")
    maximum = experience_config.get("maximum_years")
    if minimum is None and maximum is None:
        return True
    if minimum is not None and candidate_years < minimum:
        return False
    if maximum is not None and candidate_years > maximum:
        return False
    return True


def _check_education_satisfied(candidate_degrees: list[str], education_config: dict | None) -> bool:
    """Check if a candidate satisfies an education requirement."""
    if not education_config or not isinstance(education_config, dict):
        return True  # No requirement = satisfied
    level = education_config.get("level")
    requirement = education_config.get("requirement", "required")
    if not level or requirement == "optional":
        return True
    required_level = EDUCATION_LEVEL_RANK.get(level, 0)
    if required_level == 0:
        return True
    candidate_max = _max_degree_rank(candidate_degrees)
    return candidate_max >= required_level


# ─── Main Analyzer ─────────────────────────────────────────────────


class RequirementImpactAnalyzer:
    """Analyzes requirement-specific impact from persisted Phase 3 results.

    This is a READ-ONLY analyzer. It consumes SimulationResult rows
    produced by Phase 3 and configuration snapshots to decompose ranking
    impact by individual requirement changes. It never writes to live
    hiring tables.
    """

    def __init__(
        self,
        session: AsyncSession,
        execution_repo: SimulationExecutionRepository | None = None,
        result_repo: SimulationResultRepository | None = None,
        scenario_repo: SimulationRepository | None = None,
    ) -> None:
        self._session = session
        self._exec_repo = execution_repo or SimulationExecutionRepository(session)
        self._result_repo = result_repo or SimulationResultRepository(session)
        self._scenario_repo = scenario_repo or SimulationRepository(session)

    async def analyze(
        self,
        simulation_id: uuid.UUID,
        execution_id: uuid.UUID | None = None,
    ) -> RequirementImpactResponse:
        """Run the full requirement impact analysis for a simulation execution.

        Args:
            simulation_id: The simulation scenario ID.
            execution_id: Optional specific execution ID. If None, uses
                         the latest completed execution.

        Returns:
            Complete requirement impact analysis response.

        Raises:
            NotFoundError: If simulation or execution not found.
            ValidationError: If execution is not completed.
        """
        scenario = await self._scenario_repo.get(simulation_id)
        if not scenario:
            raise NotFoundError("Simulation not found")

        execution = await self._resolve_execution(scenario, execution_id)

        results = await self._result_repo.list_by_execution(execution.id)
        if not results:
            return self._empty_response(scenario, execution)

        snapshot = execution.configuration_snapshot or {}
        baseline_config = snapshot.get("baseline") or {}
        simulation_config = snapshot.get("simulation") or {}

        # Identify requirement changes
        skill_changes = _identify_skill_changes(baseline_config, simulation_config)
        exp_change = _identify_experience_change(baseline_config, simulation_config)
        edu_change = _identify_education_change(baseline_config, simulation_config)

        all_changes = list(skill_changes)
        if exp_change:
            all_changes.append(exp_change)
        if edu_change:
            all_changes.append(edu_change)

        # Compute satisfaction for each candidate
        candidate_impacts = self._compute_candidate_impacts(
            results, baseline_config, simulation_config, all_changes,
        )

        # Compute per-requirement impact metrics
        self._compute_requirement_impact_metrics(
            all_changes, candidate_impacts, results,
        )

        # Build summaries
        change_summary = self._build_change_summary(skill_changes, exp_change, edu_change)
        impact_summary = self._build_impact_summary(candidate_impacts)

        return RequirementImpactResponse(
            simulation_id=simulation_id,
            execution_id=execution.id,
            execution_status=execution.status,
            scenario_name=scenario.name,
            job_title=scenario.job.title if scenario.job else "",
            company=scenario.job.company if scenario.job else "",
            completed_at=execution.completed_at,
            change_summary=change_summary,
            impact_summary=impact_summary,
            requirement_changes=all_changes,
        )

    async def get_requirement_list(
        self,
        simulation_id: uuid.UUID,
        execution_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> RequirementImpactListResponse:
        """Get paginated list of requirement changes with impact."""
        response = await self.analyze(simulation_id, execution_id=execution_id)
        total = len(response.requirement_changes)
        start = (page - 1) * page_size
        end = start + page_size
        items = response.requirement_changes[start:end]

        return RequirementImpactListResponse(
            simulation_id=simulation_id,
            execution_id=response.execution_id,
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )

    async def get_affected_candidates(
        self,
        simulation_id: uuid.UUID,
        execution_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        requirement: str | None = None,
        requirement_type: str | None = None,
        newly_qualified: bool | None = None,
        newly_disqualified: bool | None = None,
        sort_by: str = "simulation_rank",
        order: str = "asc",
    ) -> CandidateRequirementImpactListResponse:
        """Get paginated affected candidates with filtering."""
        scenario = await self._scenario_repo.get(simulation_id)
        if not scenario:
            raise NotFoundError("Simulation not found")

        execution = await self._resolve_execution(scenario, execution_id)
        results = await self._result_repo.list_by_execution(execution.id)

        if not results:
            return CandidateRequirementImpactListResponse(
                simulation_id=simulation_id,
                execution_id=execution.id,
                total=0,
                page=page,
                page_size=page_size,
                items=[],
            )

        snapshot = execution.configuration_snapshot or {}
        baseline_config = snapshot.get("baseline") or {}
        simulation_config = snapshot.get("simulation") or {}

        skill_changes = _identify_skill_changes(baseline_config, simulation_config)
        exp_change = _identify_experience_change(baseline_config, simulation_config)
        edu_change = _identify_education_change(baseline_config, simulation_config)
        all_changes = list(skill_changes)
        if exp_change:
            all_changes.append(exp_change)
        if edu_change:
            all_changes.append(edu_change)

        candidate_impacts = self._compute_candidate_impacts(
            results, baseline_config, simulation_config, all_changes,
        )

        # Filter to only candidates with affected requirements
        candidates = [c for c in candidate_impacts if c.affected_requirements]

        # Apply filters
        if requirement:
            req_lower = requirement.lower()
            candidates = [
                c for c in candidates
                if any(req_lower in ar.requirement_name.lower() for ar in c.affected_requirements)
            ]
        if requirement_type:
            candidates = [
                c for c in candidates
                if any(ar.requirement_type == requirement_type for ar in c.affected_requirements)
            ]
        if newly_qualified is not None:
            if newly_qualified:
                candidates = [c for c in candidates if c.qualification_change == "newly_qualified"]
            else:
                candidates = [c for c in candidates if c.qualification_change != "newly_qualified"]
        if newly_disqualified is not None:
            if newly_disqualified:
                candidates = [c for c in candidates if c.qualification_change == "newly_disqualified"]
            else:
                candidates = [c for c in candidates if c.qualification_change != "newly_disqualified"]

        # Sort
        reverse = order == "desc"
        sort_keys = {
            "simulation_rank": lambda c: c.simulation_rank,
            "rank_change": lambda c: c.rank_change,
            "score_change": lambda c: c.score_change,
            "candidate_name": lambda c: c.candidate_name,
        }
        sort_fn = sort_keys.get(sort_by, sort_keys["simulation_rank"])
        candidates.sort(key=sort_fn, reverse=reverse)

        total = len(candidates)
        start = (page - 1) * page_size
        end = start + page_size
        items = candidates[start:end]

        return CandidateRequirementImpactListResponse(
            simulation_id=simulation_id,
            execution_id=execution.id,
            total=total,
            page=page,
            page_size=page_size,
            items=items,
        )

    async def get_candidate_detail(
        self,
        simulation_id: uuid.UUID,
        candidate_id: uuid.UUID,
        execution_id: uuid.UUID | None = None,
    ) -> CandidateRequirementImpactDetailResponse:
        """Get detailed requirement impact for a single candidate."""
        scenario = await self._scenario_repo.get(simulation_id)
        if not scenario:
            raise NotFoundError("Simulation not found")

        execution = await self._resolve_execution(scenario, execution_id)
        results = await self._result_repo.list_by_execution(execution.id)

        result = next((r for r in results if r.candidate_id == candidate_id), None)
        if not result:
            raise NotFoundError("Candidate result not found for this execution")

        snapshot = execution.configuration_snapshot or {}
        baseline_config = snapshot.get("baseline") or {}
        simulation_config = snapshot.get("simulation") or {}

        skill_changes = _identify_skill_changes(baseline_config, simulation_config)
        exp_change = _identify_experience_change(baseline_config, simulation_config)
        edu_change = _identify_education_change(baseline_config, simulation_config)
        all_changes = list(skill_changes)
        if exp_change:
            all_changes.append(exp_change)
        if edu_change:
            all_changes.append(edu_change)

        candidate_impacts = self._compute_candidate_impacts(
            results, baseline_config, simulation_config, all_changes,
        )

        impact = next((c for c in candidate_impacts if c.candidate_id == candidate_id), None)
        if not impact:
            # Candidate exists but no affected requirements
            impact = CandidateRequirementImpactDetail(
                candidate_id=result.candidate_id,
                candidate_name=result.candidate_name,
                baseline_score=result.baseline_score,
                simulation_score=result.simulation_score,
                score_change=result.score_change,
                baseline_rank=result.baseline_rank,
                simulation_rank=result.simulation_rank,
                rank_change=result.rank_change,
                baseline_qualified=result.baseline_status == "qualified",
                simulation_qualified=result.simulation_status == "qualified",
                qualification_change="remained_qualified" if result.baseline_status == "qualified" and result.simulation_status == "qualified" else "remained_unqualified",
                shortlist_change="retained" if result.baseline_shortlisted and result.simulation_shortlisted else "never_shortlisted",
                affected_requirements=[],
                explanation="No requirement changes affected this candidate's satisfaction status.",
            )

        baseline = {
            "score": result.baseline_score,
            "rank": result.baseline_rank,
            "status": result.baseline_status,
            "shortlisted": result.baseline_shortlisted,
            "dimensions": result.baseline_dimensions or {},
        }
        simulation = {
            "score": result.simulation_score,
            "rank": result.simulation_rank,
            "status": result.simulation_status,
            "shortlisted": result.simulation_shortlisted,
            "dimensions": result.simulation_dimensions or {},
        }
        changes = {
            "score_change": result.score_change,
            "rank_change": result.rank_change,
            "qualification_change": impact.qualification_change,
            "shortlist_change": impact.shortlist_change,
        }
        explanation = self._build_candidate_explanation(result, impact)

        return CandidateRequirementImpactDetailResponse(
            simulation_id=simulation_id,
            execution_id=execution.id,
            candidate=impact,
            baseline=baseline,
            simulation=simulation,
            changes=changes,
            explanation=explanation,
        )

    # ─── Private Methods ───────────────────────────────────────────

    async def _resolve_execution(
        self,
        scenario: SimulationScenario,
        execution_id: uuid.UUID | None,
    ) -> SimulationExecution:
        """Resolve execution: explicit ID or latest completed."""
        if execution_id is not None:
            execution = await self._exec_repo.get_for_scenario(scenario.id, execution_id)
            if not execution:
                raise NotFoundError("Execution not found")
            return execution
        execution = await self._exec_repo.latest_completed(scenario.id)
        if not execution:
            raise ValidationError(
                "No completed execution found. Run the simulation first.",
            )
        return execution

    def _empty_response(
        self,
        scenario: SimulationScenario,
        execution: SimulationExecution,
    ) -> RequirementImpactResponse:
        """Return a valid but empty analysis when no results exist."""
        return RequirementImpactResponse(
            simulation_id=scenario.id,
            execution_id=execution.id,
            execution_status=execution.status,
            scenario_name=scenario.name,
            job_title=scenario.job.title if scenario.job else "",
            company=scenario.job.company if scenario.job else "",
            completed_at=execution.completed_at,
            change_summary=RequirementChangeSummary(),
            impact_summary=RequirementImpactSummary(),
            requirement_changes=[],
        )

    def _compute_candidate_impacts(
        self,
        results: list[SimulationResult],
        baseline_config: dict,
        simulation_config: dict,
        requirement_changes: list[RequirementChangeDetail],
    ) -> list[CandidateRequirementImpactDetail]:
        """Compute per-candidate requirement satisfaction changes."""
        # Build lookup of which requirement types changed
        changed_types: dict[str, set[str]] = {}
        for change in requirement_changes:
            changed_types.setdefault(change.requirement_type, set()).add(change.requirement_name.lower())

        base_requirements = baseline_config.get("requirements") or {}
        sim_requirements = simulation_config.get("requirements") or {}
        base_skills = set(base_requirements.get("mandatory_skills") or []) | set(base_requirements.get("preferred_skills") or [])
        sim_skills = set(sim_requirements.get("mandatory_skills") or []) | set(sim_requirements.get("preferred_skills") or [])
        base_mandatory = set(base_requirements.get("mandatory_skills") or [])
        sim_mandatory = set(sim_requirements.get("mandatory_skills") or [])

        impacts: list[CandidateRequirementImpactDetail] = []

        for result in results:
            affected: list[ChangedRequirementStatus] = []

            # Check each changed skill requirement
            for change in requirement_changes:
                if change.requirement_type == "skill":
                    skill_name = change.requirement_name
                    is_mandatory_in_sim = skill_name in (sim_requirements.get("mandatory_skills") or [])
                    is_mandatory_in_base = skill_name in (base_requirements.get("mandatory_skills") or [])

                    # Baseline satisfaction
                    if change.change_type == "removed":
                        base_satisfied = True  # Requirement removed, so effectively satisfied
                    else:
                        base_satisfied = _check_skill_satisfied(
                            result.baseline_matched_skills or [],
                            result.baseline_missing_required or [],
                            result.baseline_missing_preferred or [],
                            skill_name,
                            is_mandatory_in_base,
                        )

                    # Simulation satisfaction
                    if change.change_type == "removed":
                        sim_satisfied = True  # Requirement not in simulation
                    else:
                        sim_satisfied = _check_skill_satisfied(
                            result.simulation_matched_skills or [],
                            result.simulation_missing_required or [],
                            result.simulation_missing_preferred or [],
                            skill_name,
                            is_mandatory_in_sim,
                        )

                    if base_satisfied != sim_satisfied:
                        affected.append(ChangedRequirementStatus(
                            requirement_type="skill",
                            requirement_name=skill_name,
                            baseline_satisfied=base_satisfied,
                            simulation_satisfied=sim_satisfied,
                            baseline_status="SATISFIED" if base_satisfied else "MISSING",
                            simulation_status="SATISFIED" if sim_satisfied else "MISSING",
                        ))

            # Check experience changes
            if "experience" in changed_types:
                base_exp = base_requirements.get("experience")
                sim_exp = sim_requirements.get("experience")
                candidate_years = result.candidate_experience_years or 0.0
                base_satisfied = _check_experience_satisfied(candidate_years, base_exp)
                sim_satisfied = _check_experience_satisfied(candidate_years, sim_exp)
                if base_satisfied != sim_satisfied:
                    affected.append(ChangedRequirementStatus(
                        requirement_type="experience",
                        requirement_name="experience",
                        baseline_satisfied=base_satisfied,
                        simulation_satisfied=sim_satisfied,
                        baseline_status="SATISFIED" if base_satisfied else "MISSING",
                        simulation_status="SATISFIED" if sim_satisfied else "MISSING",
                    ))

            # Check education changes
            if "education" in changed_types:
                base_edu = base_requirements.get("education")
                sim_edu = sim_requirements.get("education")
                candidate_degrees = list(result.candidate_degrees or [])
                base_satisfied = _check_education_satisfied(candidate_degrees, base_edu)
                sim_satisfied = _check_education_satisfied(candidate_degrees, sim_edu)
                if base_satisfied != sim_satisfied:
                    affected.append(ChangedRequirementStatus(
                        requirement_type="education",
                        requirement_name="education",
                        baseline_satisfied=base_satisfied,
                        simulation_satisfied=sim_satisfied,
                        baseline_status="SATISFIED" if base_satisfied else "MISSING",
                        simulation_status="SATISFIED" if sim_satisfied else "MISSING",
                    ))

            # Determine qualification and shortlist changes
            base_qualified = result.baseline_status == "qualified"
            sim_qualified = result.simulation_status == "qualified"
            if base_qualified and sim_qualified:
                qual_change = "remained_qualified"
            elif not base_qualified and sim_qualified:
                qual_change = "newly_qualified"
            elif base_qualified and not sim_qualified:
                qual_change = "newly_disqualified"
            else:
                qual_change = "remained_unqualified"

            if result.baseline_shortlisted and result.simulation_shortlisted:
                short_change = "retained"
            elif not result.baseline_shortlisted and result.simulation_shortlisted:
                short_change = "entered"
            elif result.baseline_shortlisted and not result.simulation_shortlisted:
                short_change = "left"
            else:
                short_change = "never_shortlisted"

            impacts.append(CandidateRequirementImpactDetail(
                candidate_id=result.candidate_id,
                candidate_name=result.candidate_name,
                baseline_score=result.baseline_score,
                simulation_score=result.simulation_score,
                score_change=result.score_change,
                baseline_rank=result.baseline_rank,
                simulation_rank=result.simulation_rank,
                rank_change=result.rank_change,
                baseline_qualified=base_qualified,
                simulation_qualified=sim_qualified,
                qualification_change=qual_change,
                shortlist_change=short_change,
                affected_requirements=affected,
            ))

        return impacts

    def _compute_requirement_impact_metrics(
        self,
        requirement_changes: list[RequirementChangeDetail],
        candidate_impacts: list[CandidateRequirementImpactDetail],
        results: list[SimulationResult],
    ) -> None:
        """Compute per-requirement impact metrics (mutates in place)."""
        for change in requirement_changes:
            affected_count = 0
            newly_disq = 0
            newly_qual = 0
            score_impacts: list[int] = []

            for ci in candidate_impacts:
                for ar in ci.affected_requirements:
                    if (
                        ar.requirement_type == change.requirement_type
                        and ar.requirement_name.lower() == change.requirement_name.lower()
                    ):
                        affected_count += 1
                        if ci.qualification_change == "newly_disqualified":
                            newly_disq += 1
                        if ci.qualification_change == "newly_qualified":
                            newly_qual += 1
                        score_impacts.append(ci.score_change)
                        break

            change.affected_candidates = affected_count
            change.newly_disqualified = newly_disq
            change.newly_qualified = newly_qual
            change.avg_score_impact = round(
                _safe_divide(sum(score_impacts), len(score_impacts), 0.0), 2,
            ) if score_impacts else 0.0
            change.impact_category = _impact_category(affected_count)

    def _build_change_summary(
        self,
        skill_changes: list[RequirementChangeDetail],
        exp_change: RequirementChangeDetail | None,
        edu_change: RequirementChangeDetail | None,
    ) -> RequirementChangeSummary:
        """Build aggregate change summary."""
        return RequirementChangeSummary(
            total_requirements_changed=len(skill_changes) + (1 if exp_change else 0) + (1 if edu_change else 0),
            skills_added=sum(1 for c in skill_changes if c.change_type == "added"),
            skills_removed=sum(1 for c in skill_changes if c.change_type == "removed"),
            skills_promoted=sum(1 for c in skill_changes if c.change_type == "promoted"),
            skills_demoted=sum(1 for c in skill_changes if c.change_type == "demoted"),
            experience_changed=exp_change is not None,
            education_changed=edu_change is not None,
        )

    def _build_impact_summary(
        self,
        candidate_impacts: list[CandidateRequirementImpactDetail],
    ) -> RequirementImpactSummary:
        """Build aggregate impact summary."""
        affected = sum(1 for c in candidate_impacts if c.affected_requirements)
        return RequirementImpactSummary(
            candidates_affected=affected,
            candidates_newly_qualified=sum(1 for c in candidate_impacts if c.qualification_change == "newly_qualified"),
            candidates_newly_disqualified=sum(1 for c in candidate_impacts if c.qualification_change == "newly_disqualified"),
            candidates_score_changed=sum(1 for c in candidate_impacts if c.score_change != 0),
            candidates_rank_changed=sum(1 for c in candidate_impacts if c.rank_change != 0),
            candidates_shortlist_changed=sum(
                1 for c in candidate_impacts
                if c.shortlist_change in ("entered", "left")
            ),
        )

    @staticmethod
    def _build_candidate_explanation(
        result: SimulationResult,
        impact: CandidateRequirementImpactDetail,
    ) -> str:
        """Build a factual explanation for a single candidate's requirement impact."""
        parts: list[str] = []

        if impact.affected_requirements:
            req_names = [ar.requirement_name for ar in impact.affected_requirements]
            parts.append(
                f"Candidate affected by {len(impact.affected_requirements)} changed requirement(s): "
                f"{', '.join(req_names)}."
            )
        else:
            parts.append("No requirement changes affected this candidate's satisfaction status.")

        if impact.score_change != 0:
            sign = "+" if impact.score_change > 0 else ""
            parts.append(
                f"Score changed by {sign}{impact.score_change} "
                f"({result.baseline_score} -> {result.simulation_score})."
            )

        if impact.rank_change != 0:
            direction = "improved" if impact.rank_change > 0 else "declined"
            parts.append(
                f"Rank {direction} from #{result.baseline_rank} to #{result.simulation_rank} "
                f"({impact.rank_change:+d})."
            )

        if impact.qualification_change == "newly_disqualified":
            parts.append("Candidate is no longer qualified under the simulated requirements.")
        elif impact.qualification_change == "newly_qualified":
            parts.append("Candidate now qualifies under the simulated requirements.")

        if impact.shortlist_change == "entered":
            parts.append("Candidate entered the simulated shortlist.")
        elif impact.shortlist_change == "left":
            parts.append("Candidate left the simulated shortlist.")

        return " ".join(parts)[:500]


# ─── Candidate Data Extraction Helpers ─────────────────────────────
# These extract candidate data from SimulationResult dimension snapshots.
# For requirement satisfaction checks, we need the actual candidate data,
# but we store only dimension scores in SimulationResult. We use the
# dimension scores as a proxy where possible, and for skill satisfaction
# we rely on the matched_skills/missing_required data embedded in dimensions.

def _get_candidate_skills_from_result(result: SimulationResult) -> list[str]:
    """Extract candidate skills from result using persisted satisfaction data."""
    return list(result.baseline_matched_skills or [])


def _get_candidate_experience_from_result(result: SimulationResult) -> float:
    """Extract candidate experience years from result."""
    return result.candidate_experience_years or 0.0


def _get_candidate_degrees_from_result(result: SimulationResult) -> list[str]:
    """Extract candidate degrees from result."""
    return list(result.candidate_degrees or [])
