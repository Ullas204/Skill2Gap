"""SimulationExecutionService — Phase 3 real what-if execution engine.

A simulation execution is a READ-ONLY analytical pass over the live candidate
pool. The engine:

- snapshots the evaluated configuration (baseline + hypothetical + job context
  + candidate pool) onto a ``SimulationExecution`` row;
- loads each candidate's profile read-only and scores it twice with the SAME
  pure primitives (``app.services.simulation.evaluation``, which delegates to
  ``MatchingEngine``) — once under the baseline config, once under the
  hypothetical config;
- persists ONLY simulation-scoped rows (execution / results / impacts);
- drives the scenario lifecycle queued -> running -> completed (or failed /
  cancelled) and emits audit events at every transition.

Live hiring data (JobDescription, ScreeningResult, CandidateRanking, candidates,
shortlists) is never created or modified here. The critical acceptance test for
Phase 3 asserts Job + CandidateRanking rows are byte-for-byte unchanged after a
run.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.core.logging import get_logger
from app.domain.enums import AuditEventType, SimulationStatus
from app.domain.models import Job, User
from app.domain.simulation_models import (
    SimulationExecution,
    SimulationImpact,
    SimulationResult,
    SimulationScenario,
)
from app.domain.simulation_schemas import (
    SimulationExecutionListResponse,
    SimulationExecutionResponse,
    SimulationImpactMetric,
    SimulationResultItem,
    SimulationResultsResponse,
    SimulationSummaryResponse,
)
from app.repositories.screening.screening import ScreeningResultRepository
from app.repositories.jobs.job import JobApplicationRepository, JobRepository
from app.repositories.simulation import SimulationRepository
from app.repositories.simulation_execution import (
    SimulationExecutionRepository,
    SimulationImpactRepository,
    SimulationResultRepository,
)
from app.services.audit_service import AuditService
from app.services.screening.screening_service import ScreeningService
from app.services.simulation import evaluation
from app.services.simulation.configuration_validator import SimulationConfigurationValidator
from app.services.simulation.simulation_service import SimulationScenarioService

logger = get_logger(__name__)

ENGINE_VERSION = "simulation-phase3-v1"

PROGRESS_BATCH = 20

_QUALIFIED = "qualified"
_NOT_QUALIFIED = "not_qualified"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class SimulationExecutionService:
    def __init__(
        self,
        session: AsyncSession,
        execution_repo: SimulationExecutionRepository | None = None,
        result_repo: SimulationResultRepository | None = None,
        impact_repo: SimulationImpactRepository | None = None,
        scenario_service: SimulationScenarioService | None = None,
        screening_service: ScreeningService | None = None,
        application_repo: JobApplicationRepository | None = None,
        audit_service: AuditService | None = None,
    ) -> None:
        self._session = session
        self._exec_repo = execution_repo or SimulationExecutionRepository(session)
        self._result_repo = result_repo or SimulationResultRepository(session)
        self._impact_repo = impact_repo or SimulationImpactRepository(session)
        self._scenario_service = scenario_service or SimulationScenarioService(session)
        self._screening_service = screening_service or ScreeningService(session)
        self._app_repo = application_repo or JobApplicationRepository(session)
        self._audit_service = audit_service or AuditService(session)

    # ─── access helpers (delegated to the Phase 1/2 service) ────────

    async def _load_scenario_or_404(self, simulation_id: uuid.UUID) -> SimulationScenario:
        scenario = await self._scenario_service._load_or_404(simulation_id)
        return scenario

    async def _require_view(self, user: User, scenario: SimulationScenario) -> None:
        await self._scenario_service._require_view(user, scenario)

    async def _require_modify(self, user: User, scenario: SimulationScenario) -> None:
        await self._scenario_service._require_modify(user, scenario)

    async def _audit(
        self,
        event: AuditEventType,
        action: str,
        user: User | None,
        scenario: SimulationScenario | None,
        execution: SimulationExecution | None,
        details: dict | None,
        success: bool = True,
    ) -> None:
        await self._audit_service.log(
            event_type=event,
            action=action,
            user_id=user.id if user else (scenario.created_by if scenario else (execution.created_by if execution else None)),
            organization_id=(
                scenario.organization_id
                if scenario
                else (execution.organization_id if execution else None)
            ),
            resource_type="simulation_execution",
            resource_id=str(execution.id) if execution else str(scenario.id) if scenario else "unknown",
            details=details or {
                "job_id": str(scenario.job_id) if scenario else str(execution.job_id) if execution else None,
            },
            success=success,
        )

    # ─── run lifecycle ───────────────────────────────────────────────

    async def run_scenario(
        self,
        user: User,
        simulation_id: uuid.UUID,
        celery_task_id: str | None = None,
    ) -> SimulationExecutionResponse:
        scenario = await self._load_scenario_or_404(simulation_id)
        await self._require_modify(user, scenario)

        if scenario.status in (SimulationStatus.DRAFT.value, SimulationStatus.CANCELLED.value):
            raise ValidationError(
                f"A scenario in '{scenario.status}' cannot be executed. Mark it ready first.",
            )
        if scenario.status not in {
            SimulationStatus.READY.value,
            SimulationStatus.COMPLETED.value,
            SimulationStatus.FAILED.value,
        }:
            raise ValidationError(
                f"Cannot execute a scenario in '{scenario.status}' state.",
            )

        if await self._exec_repo.has_active(scenario.id):
            raise ConflictError(
                "This simulation already has a queued or running execution.",
            )

        if not scenario.simulation_config:
            raise ValidationError(
                "No simulation configuration recorded. Configure the scenario before running.",
            )

        valid, issues = SimulationConfigurationValidator.validate(scenario.simulation_config)
        if not valid:
            messages = "; ".join(issue.message for issue in issues[:5])
            raise ValidationError(
                f"Configuration is invalid and cannot be executed: {messages}",
                extra={"validation_errors": [issue.model_dump() for issue in issues]},
            )

        job = await self._session.get(Job, scenario.job_id)
        if not job:
            raise NotFoundError("Job not found")

        applications = await self._app_repo.list_by_job(job.id)
        candidate_ids = sorted({str(app.candidate_id) for app in applications})
        now = _utcnow()
        snapshot = {
            "snapshot_version": ENGINE_VERSION,
            "captured_at": now.isoformat(),
            "job": {
                "id": str(job.id),
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "employment_type": (
                    job.employment_type.value
                    if hasattr(job.employment_type, "value")
                    else str(job.employment_type)
                ),
                "description": job.description,
                "version": job.version,
            },
            "baseline": scenario.baseline_config,
            "simulation": scenario.simulation_config,
            "candidate_ids": candidate_ids,
        }

        execution = await self._exec_repo.create(
            scenario_id=scenario.id,
            organization_id=scenario.organization_id,
            job_id=job.id,
            created_by=user.id,
            status=SimulationStatus.QUEUED.value,
            progress=0,
            total_candidates=len(candidate_ids),
            processed_candidates=0,
            engine_version=ENGINE_VERSION,
            configuration_snapshot=snapshot,
            celery_task_id=celery_task_id,
        )
        await self._session.flush()

        await self._scenario_service._repo.update(
            scenario.id, status=SimulationStatus.QUEUED.value, completed_at=None,
        )
        await self._audit(
            AuditEventType.SIMULATION_RUN_STARTED,
            "simulation_run_started",
            user,
            scenario,
            execution,
            {"job_id": str(job.id), "candidate_count": len(candidate_ids)},
        )
        logger.info(
            "Simulation queued: execution=%s scenario=%s candidates=%d",
            execution.id, scenario.id, len(candidate_ids),
        )
        return SimulationExecutionResponse.model_validate(
            await self._load_execution(scenario.id, execution.id),
        )

    async def execute(self, execution_id: uuid.UUID) -> SimulationExecution:
        """Run the execution to completion (or failure).

        Intentionally idempotent: completed/cancelled executions are returned
        untouched, and running executions are treated as already in-flight, so
        a retried Celery message can never double-write results. On error the
        execution + scenario are transitioned to ``failed`` (never left in
        ``running``) with a sanitized error message.
        """
        execution = await self._exec_repo.get(execution_id)
        if not execution:
            raise NotFoundError("Simulation execution not found")
        if execution.status in (SimulationStatus.COMPLETED.value, SimulationStatus.CANCELLED.value):
            return execution
        if execution.status == SimulationStatus.RUNNING.value:
            return execution

        now = _utcnow()
        execution.status = SimulationStatus.RUNNING.value
        execution.started_at = now
        execution.error_message = None
        execution.progress = 0
        await self._session.flush()

        scenario = await self._scenario_service._repo.get(execution.scenario_id)
        if scenario and scenario.status not in (SimulationStatus.CANCELLED.value,):
            scenario.status = SimulationStatus.RUNNING.value
        await self._session.flush()

        try:
            snapshot = execution.configuration_snapshot
            baseline = snapshot.get("baseline") or {}
            simulation = snapshot.get("simulation") or {}
            job_info = snapshot.get("job") or {}
            candidate_ids = [uuid.UUID(cid) for cid in snapshot.get("candidate_ids", [])]

            valid, issues = SimulationConfigurationValidator.validate(simulation)
            if not valid:
                messages = "; ".join(issue.message for issue in issues[:5])
                raise ValueError(f"Invalid simulation configuration: {messages}")

            job_context = evaluation.JobContext(
                title=str(job_info.get("title", "")),
                location=str(job_info.get("location", "")),
                employment_type=str(job_info.get("employment_type", "")),
                description=str(job_info.get("description", "")),
            )

            total = len(candidate_ids)
            processed = 0
            scored: list[tuple] = []
            for candidate_id in candidate_ids:
                payload = await self._load_candidate_payload(candidate_id)
                base_eval = evaluation.evaluate_configuration(payload, job_context, baseline)
                sim_eval = evaluation.evaluate_configuration(payload, job_context, simulation)
                scored.append((candidate_id, payload, base_eval, sim_eval))
                processed += 1
                if processed % PROGRESS_BATCH == 0 or processed == total:
                    await self._set_progress(execution.id, processed, max(total, 1))
                    if execution.status == SimulationStatus.CANCELLED.value:
                        return execution

            results = await self._persist_results(
                execution, scenario, scored, baseline, simulation,
            )
            summary = self._build_summary(results, baseline, simulation)
            await self._persist_impacts(execution, summary)

            execution.status = SimulationStatus.COMPLETED.value
            execution.progress = 100
            execution.processed_candidates = total
            execution.summary = summary
            execution.completed_at = _utcnow()
            if scenario:
                scenario.status = SimulationStatus.COMPLETED.value
                scenario.completed_at = _utcnow()
            await self._session.flush()
            await self._audit(
                AuditEventType.SIMULATION_RUN_COMPLETED,
                "simulation_run_completed",
                None,
                scenario,
                execution,
                {"candidate_count": total, "summary": summary},
            )
            logger.info(
                "Simulation completed: execution=%s scenario=%s candidates=%d",
                execution.id, execution.scenario_id, total,
            )
        except Exception as exc:
            logger.exception("Simulation execution failed: execution=%s", execution.id)
            execution.status = SimulationStatus.FAILED.value
            execution.error_message = str(exc)[:1000]
            execution.failed_at = _utcnow()
            if scenario and scenario.status not in (SimulationStatus.CANCELLED.value,):
                scenario.status = SimulationStatus.FAILED.value
            await self._session.flush()
            await self._audit(
                AuditEventType.SIMULATION_RUN_FAILED,
                "simulation_run_failed",
                None,
                scenario,
                execution,
                {"error": str(exc)[:500]},
                success=False,
            )
        return await self._load_execution(execution.scenario_id, execution.id)

    async def cancel_execution(
        self,
        user: User,
        simulation_id: uuid.UUID,
        execution_id: uuid.UUID,
    ) -> SimulationExecutionResponse:
        scenario = await self._load_scenario_or_404(simulation_id)
        await self._require_modify(user, scenario)
        execution = await self._exec_repo.get_for_scenario(simulation_id, execution_id)
        if not execution:
            raise NotFoundError("Simulation execution not found")
        if execution.status not in (
            SimulationStatus.QUEUED.value,
            SimulationStatus.RUNNING.value,
        ):
            raise ConflictError(
                f"Only queued or running executions can be cancelled (status: {execution.status}).",
            )
        now = _utcnow()
        execution.status = SimulationStatus.CANCELLED.value
        execution.cancelled_at = now
        # Scenario status mirrors the execution (cancelled), matching how
        # completed/failed are mirrored on the scenario after a run.
        scenario.status = SimulationStatus.CANCELLED.value
        scenario.completed_at = None
        await self._session.flush()
        await self._audit(
            AuditEventType.SIMULATION_RUN_CANCELLED,
            "simulation_run_cancelled",
            user,
            scenario,
            execution,
            {"job_id": str(scenario.job_id)},
        )
        logger.info("Simulation cancelled: execution=%s scenario=%s", execution.id, simulation_id)
        return SimulationExecutionResponse.model_validate(
            await self._load_execution(scenario.id, execution.id),
        )

    # ─── queries ─────────────────────────────────────────────────────

    async def get_execution(
        self, user: User, simulation_id: uuid.UUID, execution_id: uuid.UUID,
    ) -> SimulationExecutionResponse:
        scenario = await self._load_scenario_or_404(simulation_id)
        await self._require_view(user, scenario)
        execution = await self._exec_repo.get_for_scenario(simulation_id, execution_id)
        if not execution:
            raise NotFoundError("Simulation execution not found")
        return SimulationExecutionResponse.model_validate(execution)

    async def list_executions(
        self, user: User, simulation_id: uuid.UUID,
    ) -> SimulationExecutionListResponse:
        scenario = await self._load_scenario_or_404(simulation_id)
        await self._require_view(user, scenario)
        executions = await self._exec_repo.list_by_scenario(simulation_id)
        return SimulationExecutionListResponse(
            scenario_id=simulation_id,
            items=[SimulationExecutionResponse.model_validate(e) for e in executions],
        )

    async def list_results(
        self,
        user: User,
        simulation_id: uuid.UUID,
        execution_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "simulation_rank",
        order: str = "asc",
        change_filter: str | None = None,
    ) -> SimulationResultsResponse:
        scenario = await self._load_scenario_or_404(simulation_id)
        await self._require_view(user, scenario)
        execution = await self._resolve_execution(user, scenario, execution_id)
        if not execution:
            return SimulationResultsResponse(
                scenario_id=simulation_id,
                execution_id=execution_id or uuid.UUID(int=0),
                total=0,
                page=page,
                page_size=page_size,
            )
        items, total = await self._result_repo.paginated(
            execution.id,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            order=order,
            change_filter=change_filter,
        )
        return SimulationResultsResponse(
            scenario_id=simulation_id,
            execution_id=execution.id,
            total=total,
            page=page,
            page_size=page_size,
            items=[SimulationResultItem.model_validate(item) for item in items],
        )

    async def get_summary(
        self, user: User, simulation_id: uuid.UUID, execution_id: uuid.UUID | None = None,
    ) -> SimulationSummaryResponse:
        scenario = await self._load_scenario_or_404(simulation_id)
        await self._require_view(user, scenario)
        execution = await self._resolve_execution(user, scenario, execution_id)
        if not execution:
            return SimulationSummaryResponse(
                scenario_id=simulation_id,
                execution_id=execution_id or uuid.UUID(int=0),
                status="no_execution",
                engine_version=ENGINE_VERSION,
                total_candidates=0,
                processed_candidates=0,
                threshold_baseline=0,
                threshold_simulation=0,
                shortlist_baseline=0,
                shortlist_simulation=0,
            )

        baseline = (execution.configuration_snapshot or {}).get("baseline") or {}
        simulation = (execution.configuration_snapshot or {}).get("simulation") or {}
        impacts = await self._impact_repo.list_by_execution(execution.id)
        movers = await self._result_repo.top_movers(execution.id, limit=5)
        return SimulationSummaryResponse(
            scenario_id=simulation_id,
            execution_id=execution.id,
            status=execution.status,
            engine_version=execution.engine_version,
            total_candidates=execution.total_candidates,
            processed_candidates=execution.processed_candidates,
            threshold_baseline=int(baseline.get("threshold", 70)),
            threshold_simulation=int(simulation.get("threshold", 70)),
            shortlist_baseline=int(baseline.get("shortlist_size", 10)),
            shortlist_simulation=int(simulation.get("shortlist_size", 10)),
            summary=execution.summary or {},
            metrics=[SimulationImpactMetric.model_validate(m) for m in impacts],
            major_movements=[SimulationResultItem.model_validate(m) for m in movers],
            completed_at=execution.completed_at,
            error_message=execution.error_message,
        )

    # ─── internals ───────────────────────────────────────────────────

    async def _resolve_execution(
        self,
        user: User,
        scenario: SimulationScenario,
        execution_id: uuid.UUID | None,
    ) -> SimulationExecution | None:
        if execution_id is not None:
            execution = await self._exec_repo.get_for_scenario(scenario.id, execution_id)
            if not execution:
                raise NotFoundError("Simulation execution not found")
            await self._require_view(user, scenario)
            return execution
        return await self._exec_repo.latest_completed(scenario.id)

    async def _load_execution(
        self, scenario_id: uuid.UUID, execution_id: uuid.UUID,
    ) -> SimulationExecution:
        execution = await self._exec_repo.get_for_scenario(scenario_id, execution_id)
        if not execution:
            raise NotFoundError("Simulation execution not found")
        return execution

    async def _set_progress(self, execution_id: uuid.UUID, processed: int, total: int) -> None:
        execution = await self._exec_repo.get(execution_id)
        if not execution:
            return
        execution.processed_candidates = processed
        execution.progress = int(processed / total * 100) if total else 0
        await self._session.flush()

    async def _load_candidate_payload(self, candidate_id: uuid.UUID) -> evaluation.CandidatePayload:
        svc = self._screening_service
        user = await self._session.get(User, candidate_id)
        name = user.full_name if user else "Unknown candidate"
        profile = await svc.profile_repo.get_by_user_id(candidate_id)
        if not profile:
            return evaluation.CandidatePayload(
                candidate_id=candidate_id, candidate_name=name,
            )
        skills = await svc._get_candidate_skill_names(profile)
        degrees = await svc._get_candidate_degrees(profile)
        experiences = await svc._get_experiences(profile)
        years = ScreeningService._calculate_total_experience(experiences)
        emp_pref = ScreeningService._get_candidate_employment_preference(experiences)
        project_count, project_techs = await svc._get_project_info(profile)
        certifications = await svc._get_candidate_certifications(profile)
        resume_text = ""
        resume = await svc.resume_repo.get_primary(candidate_id)
        if resume:
            parsed = await svc.parsed_repo.get_by_resume(resume.id)
            if parsed:
                resume_text = parsed.raw_text or ""
        return evaluation.CandidatePayload(
            candidate_id=candidate_id,
            candidate_name=name,
            skills=skills,
            experience_years=years,
            degrees=degrees,
            project_count=project_count,
            project_technologies=project_techs,
            certifications=certifications,
            location=profile.location,
            employment_preference=emp_pref,
            resume_text=resume_text,
        )

    def _build_result_rows(
        self,
        scored: list[tuple],
        baseline: dict,
        simulation: dict,
    ) -> list[SimulationResult]:
        base_evaluations = [entry[2] for entry in scored]
        sim_evaluations = [entry[3] for entry in scored]
        base_ranked = evaluation.build_rankings(
            base_evaluations, int(baseline.get("shortlist_size", 10)),
        )
        sim_ranked = evaluation.build_rankings(
            sim_evaluations, int(simulation.get("shortlist_size", 10)),
        )
        base_by_candidate = {
            e.candidate_id: (rank, short)
            for rank, e, short in base_ranked
        }
        sim_by_candidate = {
            e.candidate_id: (rank, short)
            for rank, e, short in sim_ranked
        }
        rows: list[SimulationResult] = []
        for cid, payload, base_eval, sim_eval in scored:
            base_rank, base_short = base_by_candidate[cid]
            sim_rank, sim_short = sim_by_candidate[cid]
            reason = evaluation.explain_score_change(
                base_eval, sim_eval, baseline, simulation,
            )
            rows.append(
                SimulationResult(
                    scenario_id=uuid.UUID(int=0),
                    execution_id=uuid.UUID(int=0),
                    candidate_id=cid,
                    candidate_name=payload.candidate_name,
                    baseline_score=base_eval.overall,
                    simulation_score=sim_eval.overall,
                    score_change=sim_eval.overall - base_eval.overall,
                    baseline_rank=base_rank,
                    simulation_rank=sim_rank,
                    rank_change=base_rank - sim_rank,
                    baseline_status=_QUALIFIED if base_eval.qualified else _NOT_QUALIFIED,
                    simulation_status=_QUALIFIED if sim_eval.qualified else _NOT_QUALIFIED,
                    baseline_shortlisted=base_short,
                    simulation_shortlisted=sim_short,
                    baseline_dimensions=base_eval.dimensions,
                    simulation_dimensions=sim_eval.dimensions,
                    reason=reason,
                    baseline_matched_skills=base_eval.matched_skills,
                    simulation_matched_skills=sim_eval.matched_skills,
                    baseline_missing_required=base_eval.missing_required,
                    simulation_missing_required=sim_eval.missing_required,
                    baseline_missing_preferred=base_eval.missing_preferred,
                    simulation_missing_preferred=sim_eval.missing_preferred,
                    candidate_experience_years=payload.experience_years,
                    candidate_degrees=payload.degrees,
                ),
            )
        return rows

    async def _persist_results(
        self,
        execution: SimulationExecution,
        scenario: SimulationScenario | None,
        scored: list[tuple],
        baseline: dict,
        simulation: dict,
    ) -> list[SimulationResult]:
        rows = self._build_result_rows(scored, baseline, simulation)
        for row in rows:
            row.scenario_id = execution.scenario_id
            row.execution_id = execution.id
            self._session.add(row)
        await self._session.flush()
        return rows

    def _build_summary(
        self,
        results: list[SimulationResult],
        baseline: dict,
        simulation: dict,
    ) -> dict:
        count = len(results)
        qualified_base = sum(1 for r in results if r.baseline_status == _QUALIFIED)
        qualified_sim = sum(1 for r in results if r.simulation_status == _QUALIFIED)
        shortlisted_base = sum(1 for r in results if r.baseline_shortlisted)
        shortlisted_sim = sum(1 for r in results if r.simulation_shortlisted)
        entered = sum(1 for r in results if r.simulation_shortlisted and not r.baseline_shortlisted)
        left = sum(1 for r in results if r.baseline_shortlisted and not r.simulation_shortlisted)
        improved = sum(1 for r in results if r.score_change > 0)
        declined = sum(1 for r in results if r.score_change < 0)
        unchanged = count - improved - declined

        avg_base = round(sum(r.baseline_score for r in results) / count, 1) if count else 0.0
        avg_sim = round(sum(r.simulation_score for r in results) / count, 1) if count else 0.0

        top_base = next((r for r in sorted(results, key=lambda r: (r.baseline_rank, r.candidate_name))), None)
        top_sim = next((r for r in sorted(results, key=lambda r: (r.simulation_rank, r.candidate_name))), None)
        top_changed = False
        if top_base and top_sim:
            top_changed = top_base.candidate_id != top_sim.candidate_id

        return {
            "engine_version": ENGINE_VERSION,
            "candidate_count": count,
            "threshold": {
                "baseline": int(baseline.get("threshold", 70)),
                "simulation": int(simulation.get("threshold", 70)),
            },
            "shortlist": {
                "baseline": int(baseline.get("shortlist_size", 10)),
                "simulation": int(simulation.get("shortlist_size", 10)),
            },
            "qualified": {
                "baseline": qualified_base,
                "simulation": qualified_sim,
                "change": qualified_sim - qualified_base,
            },
            "shortlisted": {
                "baseline": shortlisted_base,
                "simulation": shortlisted_sim,
                "change": shortlisted_sim - shortlisted_base,
            },
            "pool_movement": {
                "entered_shortlist": entered,
                "left_shortlist": left,
            },
            "score_movement": {
                "improved": improved,
                "declined": declined,
                "unchanged": unchanged,
            },
            "average_score": {
                "baseline": avg_base,
                "simulation": avg_sim,
                "change": round(avg_sim - avg_base, 1),
            },
            "top_candidate_changed": top_changed,
            "baseline_top_candidate": top_base.candidate_name if top_base else None,
            "simulation_top_candidate": top_sim.candidate_name if top_sim else None,
        }

    async def _persist_impacts(
        self, execution: SimulationExecution, summary: dict,
    ) -> None:
        await self._impact_repo.delete_by_execution(execution.id)
        metrics = [
            ("candidate_count", summary["candidate_count"], summary["candidate_count"], 0),
            (
                "qualified_count",
                summary["qualified"]["baseline"],
                summary["qualified"]["simulation"],
                summary["qualified"]["change"],
            ),
            (
                "shortlisted_count",
                summary["shortlisted"]["baseline"],
                summary["shortlisted"]["simulation"],
                summary["shortlisted"]["change"],
            ),
            (
                "entered_shortlist",
                summary["pool_movement"]["entered_shortlist"],
                summary["pool_movement"]["entered_shortlist"],
                0,
            ),
            (
                "left_shortlist",
                summary["pool_movement"]["left_shortlist"],
                summary["pool_movement"]["left_shortlist"],
                0,
            ),
            (
                "average_score",
                summary["average_score"]["baseline"],
                summary["average_score"]["simulation"],
                summary["average_score"]["change"],
            ),
            (
                "score_improved_count",
                summary["score_movement"]["improved"],
                summary["score_movement"]["improved"],
                0,
            ),
            (
                "score_declined_count",
                summary["score_movement"]["declined"],
                summary["score_movement"]["declined"],
                0,
            ),
            (
                "top_candidate_changed",
                1 if summary["top_candidate_changed"] else 0,
                1 if summary["top_candidate_changed"] else 0,
                0,
            ),
        ]
        for metric, base_value, sim_value, change in metrics:
            self._session.add(
                SimulationImpact(
                    execution_id=execution.id,
                    scenario_id=execution.scenario_id,
                    metric=metric,
                    baseline_value=float(base_value),
                    simulation_value=float(sim_value),
                    change_value=float(change),
                ),
            )
        await self._session.flush()