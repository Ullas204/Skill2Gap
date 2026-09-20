"""SimulationScenarioService — Phase 1 scenario management.

This service ONLY manages simulation scenarios (create, snapshot baseline,
view, update draft configuration, delete). It never runs simulation or
ranking calculations; those belong to later phases.

Tenant isolation is enforced here (service + repository layer), never only in
the frontend: the authenticated user's identity is always derived from the
request, and organization context comes from the job the scenario is created
against.
"""

import copy
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ForbiddenError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.enums import AuditEventType, SimulationStatus
from app.domain.models import Job, Role, User, UserRole
from app.domain.screening_schemas import DEFAULT_WEIGHTS
from app.domain.simulation_schemas import (
    ALLOWED_STATUS_TRANSITIONS,
    SimulationChangesResponse,
    SimulationScenarioCreate,
    SimulationScenarioListItem,
    SimulationScenarioListResponse,
    SimulationScenarioResponse,
    SimulationScenarioUpdate,
    SimulationStatsResponse,
    SimulationStatusResponse,
    SimulationValidationResponse,
)
from app.domain.simulation_models import SimulationScenario
from app.repositories.jobs.job import JobRepository
from app.repositories.membership import OrganizationMembershipRepository
from app.repositories.simulation import SimulationRepository
from app.services.audit_service import AuditService
from app.services.simulation.change_detection import compute_changes
from app.services.simulation.configuration_validator import SimulationConfigurationValidator

logger = get_logger(__name__)

EXECUTION_STATUSES = {
    SimulationStatus.QUEUED.value,
    SimulationStatus.RUNNING.value,
    SimulationStatus.COMPLETED.value,
    SimulationStatus.FAILED.value,
}

# Org membership roles that may modify other members' scenarios.
MODIFY_ORG_ROLES = {"organization_admin", "hr_manager", "hr"}


class SimulationScenarioService:
    def __init__(
        self,
        session: AsyncSession,
        simulation_repo: SimulationRepository | None = None,
        job_repo: JobRepository | None = None,
        membership_repo: OrganizationMembershipRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._session = session
        self._repo = simulation_repo or SimulationRepository(session)
        self._job_repo = job_repo or JobRepository(session)
        self._membership_repo = membership_repo or OrganizationMembershipRepository(session)
        self._audit_service = audit_service or AuditService(session)

    # ─── permission helpers ─────────────────────────────────────────

    async def _role_names(self, user: User) -> set[str]:
        # Explicit query instead of ``user.roles`` lazyload so service-level
        # callers (and async test sessions) never trigger IO outside a greenlet.
        result = await self._session.execute(
            select(Role.name)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(UserRole.user_id == user.id),
        )
        return set(result.scalars().all())

    async def _is_platform_admin(self, user: User) -> bool:
        return bool(await self._role_names(user) & {"admin", "super_admin"})

    async def _org_role(self, user: User, org_id: uuid.UUID | None) -> str | None:
        if not org_id:
            return None
        membership = await self._membership_repo.get_active_membership(user.id, org_id)
        return membership.role if membership else None

    async def _require_job_access(self, user: User, job: Job) -> None:
        """A user may target a job only if they are an active member of the
        job's organization, a platform admin, or (for org-less jobs) the job's
        creator."""
        if await self._is_platform_admin(user):
            return
        if job.organization_id:
            membership = await self._membership_repo.get_active_membership(
                user.id, job.organization_id,
            )
            if membership:
                return
        elif job.recruiter_id == user.id:
            return
        logger.warning(
            "Simulation job access denied: user=%s job=%s org=%s",
            user.id, job.id, job.organization_id,
        )
        raise ForbiddenError("You do not have access to this job")

    async def _require_view(self, user: User, scenario: SimulationScenario) -> None:
        if await self._is_platform_admin(user):
            return
        if scenario.created_by == user.id:
            return
        if scenario.organization_id:
            membership = await self._membership_repo.get_active_membership(
                user.id, scenario.organization_id,
            )
            if membership:
                return
        logger.warning(
            "Simulation view denied: user=%s scenario=%s org=%s",
            user.id, scenario.id, scenario.organization_id,
        )
        raise ForbiddenError("You do not have access to this simulation")

    async def _require_modify(self, user: User, scenario: SimulationScenario) -> None:
        if await self._is_platform_admin(user):
            return
        if scenario.created_by == user.id:
            return
        org_role = await self._org_role(user, scenario.organization_id)
        if org_role in MODIFY_ORG_ROLES:
            return
        logger.warning(
            "Simulation modify denied: user=%s scenario=%s org_role=%s",
            user.id, scenario.id, org_role,
        )
        raise ForbiddenError("You may not modify this simulation")

    @staticmethod
    def _require_editable(scenario: SimulationScenario) -> None:
        if scenario.status not in SimulationStatus.editable_states():
            raise ValidationError(
                f"Scenario must be in a draft state to be edited (current: {scenario.status})",
            )

    # ─── snapshot / serialization helpers ──────────────────────────

    @staticmethod
    def _build_baseline(job: Job) -> dict:
        """Snapshot of the job's current hiring configuration.

        This is a snapshot, not a reference: later changes to the job must not
        alter already-created simulations. Weights, threshold and shortlist use
        the platform's current engine defaults because the screening engine
        does not persist a per-job weight set today.
        """
        return {
            "source": "job_snapshot",
            "job_id": str(job.id),
            "job_version": job.version,
            "title": job.title,
            "company": job.company,
            "scoring_weights": DEFAULT_WEIGHTS.model_dump(),
            "threshold": 70,
            "shortlist_size": 10,
            "requirements": {
                "mandatory_skills": list(job.required_skills or []),
                "preferred_skills": list(job.preferred_skills or []),
                "experience_required": job.experience_required,
                "education_required": job.education_required,
            },
        }

    @staticmethod
    def _to_response(
        scenario: SimulationScenario,
        job_title: str = "",
        company: str = "",
        created_by_name: str = "",
    ) -> SimulationScenarioResponse:
        response = SimulationScenarioResponse.model_validate(scenario)
        return response.model_copy(
            update={
                "job_title": job_title or getattr(scenario.job, "title", ""),
                "company": company or getattr(scenario.job, "company", ""),
                "created_by_name": created_by_name or getattr(scenario.creator, "full_name", ""),
            },
        )

    @staticmethod
    def _to_list_item(scenario: SimulationScenario) -> SimulationScenarioListItem:
        response = SimulationScenarioListItem.model_validate(scenario)
        return response.model_copy(
            update={
                "job_title": getattr(scenario.job, "title", ""),
                "company": getattr(scenario.job, "company", ""),
                "created_by_name": getattr(scenario.creator, "full_name", ""),
            },
        )

    async def _audit(
        self,
        event: AuditEventType,
        action: str,
        user: User,
        scenario: SimulationScenario,
        details: dict | None = None,
        success: bool = True,
    ) -> None:
        await self._audit_service.log(
            event_type=event,
            action=action,
            user_id=user.id,
            organization_id=scenario.organization_id,
            resource_type="simulation_scenario",
            resource_id=str(scenario.id),
            details=details or {"job_id": str(scenario.job_id)},
            success=success,
        )

    async def _load_or_404(self, simulation_id: uuid.UUID) -> SimulationScenario:
        scenario = await self._repo.get_with_details(simulation_id)
        if not scenario:
            raise NotFoundError("Simulation scenario not found")
        return scenario

    # ─── public operations ─────────────────────────────────────────

    async def create_scenario(self, user: User, data: SimulationScenarioCreate) -> SimulationScenarioResponse:
        job = await self._job_repo.get(data.job_id)
        if not job:
            raise NotFoundError("Job not found")
        await self._require_job_access(user, job)

        baseline = self._build_baseline(job)
        if data.simulation_config:
            simulation_config = data.simulation_config.model_dump(mode="json")
        else:
            # Default the experiment to the job's current configuration so the
            # baseline-vs-simulation comparison is meaningful out of the box.
            simulation_config = {
                "scoring_weights": copy.deepcopy(baseline["scoring_weights"]),
                "threshold": baseline["threshold"],
                "shortlist_size": baseline["shortlist_size"],
                "requirements": copy.deepcopy(baseline["requirements"]),
            }
        # The persisted JSON blob mirrors the scenario's config_version so the
        # stored configuration is self-describing and versioned.
        simulation_config["version"] = 1

        scenario = await self._repo.create(
            organization_id=job.organization_id,
            job_id=job.id,
            created_by=user.id,
            name=data.name,
            description=data.description,
            status=SimulationStatus.DRAFT.value,
            baseline_config=baseline,
            simulation_config=simulation_config,
            config_version=1,
            metadata_json=data.metadata,
            completed_at=None,
        )
        await self._audit(AuditEventType.SIMULATION_CREATED, "simulation_create", user, scenario)
        logger.info(
            "Simulation created: id=%s user=%s job=%s org=%s",
            scenario.id, user.id, job.id, job.organization_id,
        )
        return self._to_response(scenario, job.title, job.company, user.full_name)

    async def get_scenario(self, user: User, simulation_id: uuid.UUID) -> SimulationScenarioResponse:
        scenario = await self._load_or_404(simulation_id)
        await self._require_view(user, scenario)
        return self._to_response(scenario)

    async def list_scenarios(self, user: User) -> SimulationScenarioListResponse:
        memberships = await self._membership_repo.get_user_organizations(user.id)
        org_ids = [m.organization_id for m in memberships]
        scenarios = await self._repo.list_visible(user.id, org_ids)

        counts = await self._repo.count_by_status(user.id, org_ids)
        stats = SimulationStatsResponse(
            total=len(scenarios),
            drafts=counts.get(SimulationStatus.DRAFT.value, 0),
            ready=counts.get(SimulationStatus.READY.value, 0),
            queued=counts.get(SimulationStatus.QUEUED.value, 0),
            running=counts.get(SimulationStatus.RUNNING.value, 0),
            completed=counts.get(SimulationStatus.COMPLETED.value, 0),
            failed=counts.get(SimulationStatus.FAILED.value, 0),
            cancelled=counts.get(SimulationStatus.CANCELLED.value, 0),
            by_status=counts,
        )
        return SimulationScenarioListResponse(
            items=[self._to_list_item(s) for s in scenarios],
            stats=stats,
        )

    async def update_scenario(
        self, user: User, simulation_id: uuid.UUID, data: SimulationScenarioUpdate,
    ) -> SimulationScenarioResponse:
        scenario = await self._load_or_404(simulation_id)
        await self._require_modify(user, scenario)
        self._require_editable(scenario)

        apply: dict = {}
        if data.name is not None:
            apply["name"] = data.name
        if data.description is not None:
            apply["description"] = data.description
        if data.metadata is not None:
            apply["metadata_json"] = data.metadata
        if data.simulation_config is not None:
            config_dict = data.simulation_config.model_dump(mode="json")
            config_dict["version"] = scenario.config_version + 1
            apply["simulation_config"] = config_dict
            apply["config_version"] = scenario.config_version + 1

        status_changed = False
        if data.status is not None:
            new_status = data.status.value
            allowed = ALLOWED_STATUS_TRANSITIONS.get(scenario.status, set())
            if new_status not in allowed:
                raise ValidationError(
                    f"Status transition not permitted: {scenario.status} -> {new_status}",
                )
            if new_status in EXECUTION_STATUSES:
                raise ValidationError(
                    "Execution statuses are reserved for the simulation engine",
                )
            if new_status == SimulationStatus.READY.value:
                # A scenario cannot be marked ready unless its full
                # configuration passes validation. Drafts may be invalid; ready
                # scenarios are treated as immutable, verified configurations.
                effective_config = apply.get("simulation_config") or scenario.simulation_config
                valid, issues = SimulationConfigurationValidator.validate(effective_config)
                if not valid:
                    messages = "; ".join(issue.message for issue in issues[:5])
                    remaining = len(issues) - 5
                    if remaining > 0:
                        messages += f" (+{remaining} more issue{'s' if remaining != 1 else ''})"
                    raise ValidationError(
                        "Configuration is not valid and cannot be marked ready: "
                        f"{messages}",
                        extra={"validation_errors": [issue.model_dump() for issue in issues]},
                    )
            status_changed = new_status != scenario.status
            apply["status"] = new_status

        if apply:
            await self._repo.update(scenario.id, **apply)
            scenario = await self._repo.get_with_details(scenario.id)
            if not scenario:
                raise NotFoundError("Simulation scenario not found")

        await self._audit(
            AuditEventType.SIMULATION_UPDATED,
            "simulation_update",
            user,
            scenario,
            details={"job_id": str(scenario.job_id), "fields": list(apply.keys())},
        )
        if status_changed:
            await self._audit(
                AuditEventType.SIMULATION_STATUS_CHANGED,
                "simulation_status_change",
                user,
                scenario,
                details={"job_id": str(scenario.job_id), "status": scenario.status},
            )
        logger.info(
            "Simulation updated: id=%s user=%s fields=%s",
            scenario.id, user.id, list(apply.keys()),
        )
        return self._to_response(scenario)

    async def delete_scenario(self, user: User, simulation_id: uuid.UUID) -> bool:
        scenario = await self._load_or_404(simulation_id)
        await self._require_modify(user, scenario)
        self._require_editable(scenario)

        await self._repo.delete(scenario.id)
        await self._audit(AuditEventType.SIMULATION_DELETED, "simulation_delete", user, scenario)
        logger.info("Simulation deleted: id=%s user=%s", scenario.id, user.id)
        return True

    async def get_status(self, user: User, simulation_id: uuid.UUID) -> SimulationStatusResponse:
        scenario = await self._load_or_404(simulation_id)
        await self._require_view(user, scenario)
        return SimulationStatusResponse(
            simulation_id=scenario.id,
            status=scenario.status,
            can_edit=scenario.status not in EXECUTION_STATUSES,
            updated_at=scenario.updated_at,
            completed_at=scenario.completed_at,
        )

    async def validate_scenario(self, user: User, simulation_id: uuid.UUID) -> SimulationValidationResponse:
        """Validate the current configuration and return structured errors.

        Read-only: nothing is persisted. The same validator that enforces the
        `ready` gate is exposed here so the builder can check live.
        """
        scenario = await self._load_or_404(simulation_id)
        await self._require_view(user, scenario)

        valid, issues = SimulationConfigurationValidator.validate(scenario.simulation_config)
        await self._audit(
            AuditEventType.SIMULATION_VALIDATED,
            "simulation_validate",
            user,
            scenario,
            details={
                "job_id": str(scenario.job_id),
                "valid": valid,
                "issue_count": len(issues),
            },
            success=valid,
        )
        logger.info(
            "Simulation validated: id=%s user=%s valid=%s issues=%d",
            scenario.id, user.id, valid, len(issues),
        )
        return SimulationValidationResponse(valid=valid, errors=issues)

    async def get_scenario_changes(
        self, user: User, simulation_id: uuid.UUID,
    ) -> SimulationChangesResponse:
        """Baseline-vs-scenario diff for the builder's review section."""
        scenario = await self._load_or_404(simulation_id)
        await self._require_view(user, scenario)
        return compute_changes(
            simulation_id=scenario.id,
            config_version=scenario.config_version,
            baseline=scenario.baseline_config,
            scenario=scenario.simulation_config,
        )