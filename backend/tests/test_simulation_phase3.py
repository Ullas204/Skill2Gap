"""Tests for Simulation Phase 3 — the real what-if execution engine.

Covers:
- evaluation primitives (determinism, rankings, experience/education logic)
- full API run lifecycle (ready -> completed via synchronous fallback)
- baseline-vs-scenario scoring, ranking, shortlist and qualification changes
- determinism across re-runs; idempotent execute()
- empty pool and missing-profile candidates
- lifecycle guards (draft cannot run, duplicate active run, cancel rules)
- failure path (invalid config at run time marks execution+scenario failed)
- pagination / filter / sort on results
- RBAC + multi-tenant isolation
- CRITICAL regression: a simulation run never creates or mutates live hiring
  rows (Job, ScreeningResult, CandidateRanking, candidates, shortlists).
"""

import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError
from app.core.security import hash_password
from app.domain.enums import (
    EmploymentType,
    JobStatus,
    MembershipStatus,
    SkillCategory,
    SkillProficiency,
)
from app.domain.models import (
    AuditLog,
    CandidateProfile,
    CandidateRanking,
    CandidateSkill,
    Certification,
    Education,
    Experience,
    Job,
    JobApplication,
    Organization,
    OrganizationMembership,
    Project,
    ScreeningResult,
    Skill,
    User,
)
from app.domain.screening_schemas import DEFAULT_WEIGHTS
from app.domain.simulation_models import SimulationExecution, SimulationImpact, SimulationResult, SimulationScenario
from app.repositories.simulation import SimulationRepository
from app.repositories.simulation_execution import SimulationExecutionRepository
from app.services.simulation import evaluation
from app.services.simulation.evaluation import CandidatePayload, JobContext, ScoredEvaluation
from app.services.simulation.configuration_validator import SimulationConfigurationValidator

PASSWORD = "Sim@12345"

BASELINE_CONFIG = {
    "source": "job_snapshot",
    "job_version": 1,
    "title": "Senior Software Engineer",
    "company": "Acme Corporation",
    "scoring_weights": DEFAULT_WEIGHTS.model_dump(),
    "threshold": 70,
    "shortlist_size": 2,
    "requirements": {
        "mandatory_skills": ["Python"],
        "preferred_skills": ["SQL", "Docker"],
        "experience_required": "3 years",
        "education_required": "Bachelor's degree",
    },
}

SIM_CONFIG = {
    "scoring_weights": {
        "skills": 0.60,
        "experience": 0.10,
        "education": 0.10,
        "projects": 0.05,
        "certifications": 0.05,
        "location": 0.05,
        "employment_type": 0.05,
        "semantic": 0.00,
    },
    "threshold": 55,
    "shortlist_size": 3,
    "requirements": {
        "mandatory_skills": ["Python"],
        "preferred_skills": ["SQL", "Docker", "FastAPI"],
    },
}


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client: AsyncClient, email: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": PASSWORD})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _create_org(session: AsyncSession, name: str, slug: str) -> Organization:
    org = Organization(name=name, slug=slug, description=f"{name} demo", status="active")
    session.add(org)
    await session.flush()
    return org


async def _add_membership(
    session: AsyncSession, user: User, org: Organization, role: str,
) -> OrganizationMembership:
    membership = OrganizationMembership(
        user_id=user.id,
        organization_id=org.id,
        role=role,
        status=MembershipStatus.ACTIVE.value,
        joined_at=datetime.now(timezone.utc),
    )
    session.add(membership)
    await session.flush()
    return membership


async def _assign_role(session: AsyncSession, user: User, role_name: str) -> None:
    from app.domain.models import Role, UserRole

    role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    assert role, f"Role {role_name!r} must exist (see conftest DEFAULT_ROLES)"
    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.flush()


async def _create_job(
    session: AsyncSession,
    recruiter: User,
    org: Organization,
) -> Job:
    job = Job(
        recruiter_id=recruiter.id,
        organization_id=org.id,
        title="Senior Software Engineer",
        company=org.name,
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME.value,
        location="Remote",
        description="Lead platform engineering with Python.",
        required_skills=["Python", "SQL", "FastAPI"],
        preferred_skills=["PostgreSQL", "Docker"],
        experience_required="3 years",
        education_required="Bachelor's degree",
        status=JobStatus.PUBLISHED.value,
    )
    session.add(job)
    await session.flush()
    return job


async def _setup_recruiter_with_org(
    session: AsyncSession,
    client: AsyncClient,
    org: Organization,
    email_prefix: str = "recruiter",
) -> tuple[User, str]:
    user = User(
        id=uuid.uuid4(),
        full_name="Recruiter One",
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password(PASSWORD),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await _assign_role(session, user, "recruiter")
    await _add_membership(session, user, org, "recruiter")
    token = await _login(client, user.email)
    return user, token


async def _make_candidate(session: AsyncSession, full_name: str) -> User:
    user = User(
        id=uuid.uuid4(),
        full_name=full_name,
        email=f"cand_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password(PASSWORD),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    return user


async def _get_or_create_skill(session: AsyncSession, name: str) -> Skill:
    skill = (
        await session.execute(select(Skill).where(Skill.name == name))
    ).scalar_one_or_none()
    if skill:
        return skill
    skill = Skill(name=name, category=SkillCategory.PROGRAMMING_LANGUAGES)
    session.add(skill)
    await session.flush()
    return skill


async def _seed_candidate(
    session: AsyncSession,
    user: User,
    location: str = "Remote",
    skills: tuple[str, ...] = (),
    experience_years: float = 0.0,
    degrees: tuple[str, ...] = (),
    employment_type: EmploymentType = EmploymentType.FULL_TIME,
) -> CandidateProfile:
    profile = CandidateProfile(user_id=user.id, location=location, current_role="Engineer")
    session.add(profile)
    await session.flush()

    for name in skills:
        skill = await _get_or_create_skill(session, name)
        session.add(
            CandidateSkill(
                profile_id=profile.id,
                skill_id=skill.id,
                proficiency=SkillProficiency.ADVANCED,
                years_of_experience=experience_years,
            ),
        )

    if experience_years > 0:
        today = date.today()
        start = date(today.year - int(experience_years), today.month, min(today.day, 28))
        session.add(
            Experience(
                profile_id=profile.id,
                company="TechCorp",
                job_title="Software Engineer",
                employment_type=employment_type,
                start_date=start,
                is_current=True,
            ),
        )

    for degree in degrees:
        session.add(
            Education(
                profile_id=profile.id,
                institution="Test University",
                degree=degree,
                start_date=date(2015, 9, 1),
                end_date=date(2019, 6, 1),
            ),
        )

    await session.flush()
    return profile


async def _apply(session: AsyncSession, job: Job, user: User) -> None:
    session.add(JobApplication(job_id=job.id, candidate_id=user.id))
    await session.flush()


async def _create_scenario_via_api(
    client: AsyncClient, token: str, job: Job, name: str, sim_config: dict,
) -> dict:
    resp = await client.post(
        "/api/v1/simulations",
        headers=_auth(token),
        json={
            "job_id": str(job.id),
            "name": name,
            "simulation_config": sim_config,
        },
    )
    assert resp.status_code == 201, resp.text
    scenario = resp.json()
    resp = await client.patch(
        f"/api/v1/simulations/{scenario['id']}",
        headers=_auth(token),
        json={"status": "ready"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _create_ready_scenario(
    session: AsyncSession,
    org: Organization,
    job: Job,
    creator: User,
    name: str = "Phase 3 Scenario",
    sim_config: dict | None = None,
):
    baseline = dict(BASELINE_CONFIG)
    baseline["job_id"] = str(job.id)
    repo = SimulationRepository(session)
    return await repo.create(
        organization_id=org.id,
        job_id=job.id,
        created_by=creator.id,
        name=name,
        status="ready",
        baseline_config=baseline,
        simulation_config=sim_config or SIM_CONFIG,
        config_version=1,
    )


async def _seed_default_pool(session: AsyncSession, job: Job) -> dict[str, User]:
    alice = await _make_candidate(session, "Alice Smith")
    await _seed_candidate(
        session, alice,
        location="Remote",
        skills=("Python", "SQL", "Docker"),
        experience_years=6.0,
        degrees=("Master of Science in CS",),
    )
    bob = await _make_candidate(session, "Bob Jones")
    await _seed_candidate(
        session, bob,
        location="Remote",
        skills=("Python",),
        experience_years=3.0,
        degrees=("Bachelor of Science in CS",),
    )
    carol = await _make_candidate(session, "Carol Lee")
    await _seed_candidate(
        session, carol,
        location="New York",
        skills=("JavaScript",),
        experience_years=1.0,
        degrees=("High School Diploma",),
    )
    for user in (alice, bob, carol):
        await _apply(session, job, user)
    return {"alice": alice, "bob": bob, "carol": carol}


# ─────────────────────────────────────────────────────────────────────
# 1. Evaluation primitives
# ─────────────────────────────────────────────────────────────────────


class TestEvaluationPrimitives:
    def test_evaluate_configuration_is_deterministic(self) -> None:
        payload = CandidatePayload(
            candidate_id=uuid.uuid4(),
            candidate_name="A",
            skills=["Python", "SQL"],
            experience_years=4.0,
            degrees=["Bachelor of Science in CS"],
            location="Remote",
        )
        job = JobContext(title="Engineer", location="Remote", employment_type="full_time", description="Python work")
        first = evaluation.evaluate_configuration(payload, job, SIM_CONFIG)
        second = evaluation.evaluate_configuration(payload, job, SIM_CONFIG)
        assert first.overall == second.overall
        assert first.dimensions == second.dimensions

    def test_build_rankings_shortlist_and_tiebreak(self) -> None:
        evals = [
            ScoredEvaluation(candidate_id=uuid.UUID(int=1), overall=70, dimensions={}, matched_skills=[], missing_required=[], missing_preferred=[], qualified=True, recommendation="strong_match"),
            ScoredEvaluation(candidate_id=uuid.UUID(int=0), overall=70, dimensions={}, matched_skills=[], missing_required=[], missing_preferred=[], qualified=True, recommendation="strong_match"),
            ScoredEvaluation(candidate_id=uuid.UUID(int=3), overall=50, dimensions={}, matched_skills=[], missing_required=[], missing_preferred=[], qualified=False, recommendation="not_recommended"),
        ]
        ranked = evaluation.build_rankings(evals, shortlist_size=2)
        assert [r for r, _, _ in ranked] == [1, 2, 3]
        assert ranked[0][1].candidate_id == uuid.UUID(int=0)
        assert [short for _, _, short in ranked] == [True, True, False]

    def test_structured_experience_range(self) -> None:
        requirements = {"experience": {"minimum_years": 3, "maximum_years": 5}}
        assert evaluation.evaluate_experience(5.0, requirements) == 100
        assert evaluation.evaluate_experience(2.0, requirements) == 60
        assert evaluation.evaluate_experience(8.0, requirements) == 50
        assert evaluation.evaluate_experience(6.0, {"experience_required": "5 years"}) == 100

    def test_structured_education_requirement(self) -> None:
        requirements = {"education": {"level": "bachelor", "requirement": "required"}}
        assert evaluation.evaluate_education(["Master of Science in CS"], requirements) == 100
        assert evaluation.evaluate_education(["High School Diploma"], requirements) == 30
        pref = dict(requirements)
        pref["education"]["requirement"] = "preferred"
        assert evaluation.evaluate_education(["High School Diploma"], pref) in (65, 30)
        optional = dict(requirements)
        optional["education"]["requirement"] = "optional"
        assert evaluation.evaluate_education(["High School Diploma"], optional) == 80

    def test_explain_score_change(self) -> None:
        payload = CandidatePayload(
            candidate_id=uuid.uuid4(), candidate_name="A",
            skills=["Python", "SQL"], experience_years=4.0,
            degrees=["Bachelor of Science in CS"], location="Remote",
        )
        job = JobContext(title="Engineer", location="Remote", employment_type="full_time", description="Python work")
        base = evaluation.evaluate_configuration(payload, job, BASELINE_CONFIG)
        sim = evaluation.evaluate_configuration(payload, job, SIM_CONFIG)
        reason = evaluation.explain_score_change(base, sim, BASELINE_CONFIG, SIM_CONFIG)
        assert isinstance(reason, str)
        if base.overall == sim.overall:
            assert "overall score unchanged" in reason
        else:
            assert f"{base.overall} -> {sim.overall}" in reason

    def test_valid_configs_pass_validator(self) -> None:
        assert SimulationConfigurationValidator.validate(BASELINE_CONFIG)[0] is True
        assert SimulationConfigurationValidator.validate(SIM_CONFIG)[0] is True

    def test_invalid_threshold_fails_validator(self) -> None:
        bad = dict(SIM_CONFIG, threshold=999)
        valid, issues = SimulationConfigurationValidator.validate(bad)
        assert valid is False
        assert any("threshold" in issue.field or "Threshold" in issue.message for issue in issues)


# ─────────────────────────────────────────────────────────────────────
# 2. Full API run lifecycle
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_completes_and_persists_results(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Run Org", f"run-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    pool = await _seed_default_pool(session, job)
    scenario = await _create_scenario_via_api(client, token, job, "Run Me", SIM_CONFIG)

    sim_id = uuid.UUID(scenario["id"])
    scenario_row = await session.get(SimulationScenario, sim_id)
    assert scenario_row is not None
    scenario_row.baseline_config["shortlist_size"] = 2
    await session.flush()

    run_resp = await client.post(
        f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token),
    )
    assert run_resp.status_code == 202, run_resp.text
    execution = run_resp.json()
    assert execution["status"] == "completed"
    assert execution["progress"] == 100
    assert execution["total_candidates"] == 3
    assert execution["processed_candidates"] == 3
    assert execution["engine_version"] == "simulation-phase3-v1"

    scenario_resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}", headers=_auth(token),
    )
    assert scenario_resp.json()["status"] == "completed"

    executions = (await client.get(
        f"/api/v1/simulations/{scenario['id']}/executions", headers=_auth(token),
    )).json()
    assert len(executions["items"]) == 1

    detail = (await client.get(
        f"/api/v1/simulations/{scenario['id']}/executions/{execution['id']}",
        headers=_auth(token),
    )).json()
    assert detail["status"] == "completed"
    assert detail["started_at"] is not None and detail["completed_at"] is not None

    results = (await client.get(
        f"/api/v1/simulations/{scenario['id']}/results", headers=_auth(token),
    )).json()
    assert results["total"] == 3
    assert results["execution_id"] == execution["id"]
    by_id = {r["candidate_id"]: r for r in results["items"]}
    assert {r["candidate_name"] for r in results["items"]} == {
        "Alice Smith", "Bob Jones", "Carol Lee",
    }
    alice = by_id[str(pool["alice"].id)]
    carol = by_id[str(pool["carol"].id)]
    assert alice["simulation_rank"] == 1
    assert carol["simulation_status"] == "not_qualified"
    assert alice["simulation_shortlisted"] is True

    ranks = [r["simulation_rank"] for r in results["items"]]
    assert sorted(ranks) == [1, 2, 3]

    baseline_short = sum(1 for r in results["items"] if r["baseline_shortlisted"])
    sim_short = sum(1 for r in results["items"] if r["simulation_shortlisted"])
    assert baseline_short == 2
    assert sim_short == 3

    summary = (await client.get(
        f"/api/v1/simulations/{scenario['id']}/summary", headers=_auth(token),
    )).json()
    assert summary["status"] == "completed"
    assert summary["threshold_baseline"] == 70
    assert summary["threshold_simulation"] == 55
    assert summary["shortlist_baseline"] == 2
    assert summary["shortlist_simulation"] == 3
    assert summary["summary"]["candidate_count"] == 3
    assert summary["summary"]["shortlisted"]["baseline"] == 2
    assert summary["summary"]["shortlisted"]["simulation"] == 3
    assert summary["summary"]["pool_movement"]["entered_shortlist"] == 1
    assert summary["summary"]["pool_movement"]["left_shortlist"] == 0
    metrics = {m["metric"]: m for m in summary["metrics"]}
    assert metrics["qualified_count"]["simulation_value"] == len(
        [r for r in results["items"] if r["simulation_status"] == "qualified"],
    )
    assert len(summary["major_movements"]) <= 5

    audits = await session.execute(
        select(AuditLog).where(AuditLog.event_type == "simulation_run_completed"),
    )
    assert len(audits.scalars().all()) == 1


@pytest.mark.asyncio
async def test_rerun_is_deterministic(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Det Org", f"det-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    await _seed_default_pool(session, job)
    scenario = await _create_scenario_via_api(client, token, job, "Det", SIM_CONFIG)

    first_run = (await client.post(
        f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token),
    )).json()
    second_run = (await client.post(
        f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token),
    )).json()
    assert second_run["status"] == "completed"

    async def _extract(execution_id: str) -> dict[str, tuple[int, int]]:
        resp = (await client.get(
            f"/api/v1/simulations/{scenario['id']}/results?execution_id={execution_id}",
            headers=_auth(token),
        )).json()
        return {
            r["candidate_id"]: (r["baseline_score"], r["simulation_score"])
            for r in resp["items"]
        }

    assert await _extract(first_run["id"]) == await _extract(second_run["id"])

    executions = (await client.get(
        f"/api/v1/simulations/{scenario['id']}/executions", headers=_auth(token),
    )).json()
    assert len(executions["items"]) == 2


@pytest.mark.asyncio
async def test_empty_pool_completes_cleanly(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Empty Org", f"empty-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    scenario = await _create_scenario_via_api(client, token, job, "No Apps", SIM_CONFIG)

    run = (await client.post(
        f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token),
    )).json()
    assert run["status"] == "completed"
    assert run["total_candidates"] == 0

    results = (await client.get(
        f"/api/v1/simulations/{scenario['id']}/results", headers=_auth(token),
    )).json()
    assert results["total"] == 0
    assert results["items"] == []

    summary = (await client.get(
        f"/api/v1/simulations/{scenario['id']}/summary", headers=_auth(token),
    )).json()
    assert summary["status"] == "completed"
    assert summary["total_candidates"] == 0


@pytest.mark.asyncio
async def test_candidate_without_profile_is_still_ranked(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Miss Org", f"miss-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    alice = await _make_candidate(session, "Alice Smith")
    await _seed_candidate(session, alice, skills=("Python",), experience_years=4.0, degrees=("Bachelor of Science in CS",))
    ghost = await _make_candidate(session, "Ghost User")
    await _apply(session, job, alice)
    await _apply(session, job, ghost)
    scenario = await _create_scenario_via_api(client, token, job, "Ghost", SIM_CONFIG)

    await client.post(f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token))

    results = (await client.get(
        f"/api/v1/simulations/{scenario['id']}/results", headers=_auth(token),
    )).json()
    assert results["total"] == 2
    by_id = {r["candidate_id"]: r for r in results["items"]}
    ghost_row = by_id[str(ghost.id)]
    alice_row = by_id[str(alice.id)]
    assert ghost_row["candidate_name"] == "Ghost User"
    assert ghost_row["simulation_score"] <= alice_row["simulation_score"]


# ─────────────────────────────────────────────────────────────────────
# 3. Lifecycle guards + failure path (service level)
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_draft_scenario_cannot_run(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Draft Org", f"draft-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    create_resp = await client.post(
        "/api/v1/simulations",
        headers=_auth(token),
        json={"job_id": str(job.id), "name": "Draft", "simulation_config": SIM_CONFIG},
    )
    sim_id = create_resp.json()["id"]
    run_resp = await client.post(f"/api/v1/simulations/{sim_id}/run", headers=_auth(token))
    assert run_resp.status_code == 422


@pytest.mark.asyncio
async def test_invalid_config_at_run_time_rejected(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Bad Org", f"bad-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    # Create a valid ready scenario, then corrupt the stored config directly so
    # it regresses post-draft. The engine gate — not the request schema — must
    # reject the run with structured validation errors.
    scenario = await _create_scenario_via_api(client, token, job, "Bad", SIM_CONFIG)
    sim_id = uuid.UUID(scenario["id"])
    scenario_row = await session.get(SimulationScenario, sim_id)
    assert scenario_row is not None
    scenario_row.simulation_config["threshold"] = 999
    await session.flush()
    run_resp = await client.post(f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token))
    assert run_resp.status_code == 422


@pytest.mark.asyncio
async def test_duplicate_active_run_is_rejected(session: AsyncSession) -> None:
    org = await _create_org(session, "Dup Org", f"dup-{uuid.uuid4().hex[:6]}")
    recruiter = User(
        id=uuid.uuid4(), full_name="Dup Bot",
        email=f"dup_{uuid.uuid4().hex[:6]}@test.com", password_hash="x", is_active=True,
    )
    session.add(recruiter)
    await session.flush()
    job = await _create_job(session, recruiter, org)
    scenario = await _create_ready_scenario(session, org, job, recruiter)

    from app.services.simulation.execution_service import SimulationExecutionService
    service = SimulationExecutionService(session)
    await service._exec_repo.create(
        scenario_id=scenario.id,
        organization_id=org.id,
        job_id=job.id,
        created_by=recruiter.id,
        status="queued",
        progress=0,
        total_candidates=0,
        processed_candidates=0,
        engine_version="test",
        configuration_snapshot={"baseline": BASELINE_CONFIG, "simulation": SIM_CONFIG, "candidate_ids": []},
    )
    with pytest.raises(ConflictError):
        await service.run_scenario(recruiter, scenario.id)


@pytest.mark.asyncio
async def test_cancel_execution(session: AsyncSession) -> None:
    org = await _create_org(session, "Cancel Org", f"cancel-{uuid.uuid4().hex[:6]}")
    recruiter = User(
        id=uuid.uuid4(), full_name="Cancel Bot",
        email=f"cancel_{uuid.uuid4().hex[:6]}@test.com", password_hash="x", is_active=True,
    )
    session.add(recruiter)
    await session.flush()
    job = await _create_job(session, recruiter, org)
    scenario = await _create_ready_scenario(session, org, job, recruiter)

    from app.services.simulation.execution_service import SimulationExecutionService
    service = SimulationExecutionService(session)
    execution = await service._exec_repo.create(
        scenario_id=scenario.id,
        organization_id=org.id,
        job_id=job.id,
        created_by=recruiter.id,
        status="running",
        progress=40,
        total_candidates=5,
        processed_candidates=2,
        engine_version="test",
        configuration_snapshot={"baseline": BASELINE_CONFIG, "simulation": SIM_CONFIG, "candidate_ids": []},
    )
    cancelled = await service.cancel_execution(recruiter, scenario.id, execution.id)
    assert cancelled.status == "cancelled"

    scenario_row = await SimulationRepository(session).get(scenario.id)
    assert scenario_row.status == "cancelled"

    with pytest.raises(ConflictError):
        await service.cancel_execution(recruiter, scenario.id, execution.id)


@pytest.mark.asyncio
async def test_failure_marks_execution_and_scenario_failed(session: AsyncSession) -> None:
    org = await _create_org(session, "Fail Org", f"fail-{uuid.uuid4().hex[:6]}")
    recruiter = User(
        id=uuid.uuid4(), full_name="Fail Bot",
        email=f"fail_{uuid.uuid4().hex[:6]}@test.com", password_hash="x", is_active=True,
    )
    session.add(recruiter)
    await session.flush()
    job = await _create_job(session, recruiter, org)
    scenario = await _create_ready_scenario(session, org, job, recruiter)

    from app.services.simulation.execution_service import SimulationExecutionService
    service = SimulationExecutionService(session)
    invalid_snapshot = {
        "baseline": BASELINE_CONFIG,
        "simulation": dict(SIM_CONFIG, threshold=999),
        "candidate_ids": [],
        "job": {"title": "x", "location": "", "employment_type": "full_time", "description": ""},
    }
    execution = await service._exec_repo.create(
        scenario_id=scenario.id,
        organization_id=org.id,
        job_id=job.id,
        created_by=recruiter.id,
        status="queued",
        progress=0,
        total_candidates=0,
        processed_candidates=0,
        engine_version="test",
        configuration_snapshot=invalid_snapshot,
    )

    result = await service.execute(execution.id)
    assert result.status == "failed"
    assert result.error_message and "threshold" in result.error_message.lower()

    scenario_row = await SimulationRepository(session).get(scenario.id)
    assert scenario_row.status == "failed"

    audits = (await session.execute(
        select(AuditLog).where(AuditLog.event_type == "simulation_run_failed"),
    )).scalars().all()
    assert len(audits) == 1


@pytest.mark.asyncio
async def test_execute_is_idempotent(session: AsyncSession) -> None:
    org = await _create_org(session, "Idem Org", f"idem-{uuid.uuid4().hex[:6]}")
    recruiter = User(
        id=uuid.uuid4(), full_name="Idem Bot",
        email=f"idem_{uuid.uuid4().hex[:6]}@test.com", password_hash="x", is_active=True,
    )
    session.add(recruiter)
    await session.flush()
    job = await _create_job(session, recruiter, org)
    alice = await _make_candidate(session, "Alice Smith")
    await _seed_candidate(session, alice, skills=("Python",), experience_years=4.0, degrees=("Bachelor of Science in CS",))
    await _apply(session, job, alice)
    scenario = await _create_ready_scenario(session, org, job, recruiter)

    from app.services.simulation.execution_service import SimulationExecutionService
    service = SimulationExecutionService(session)
    execution = await service._exec_repo.create(
        scenario_id=scenario.id,
        organization_id=org.id,
        job_id=job.id,
        created_by=recruiter.id,
        status="queued",
        progress=0,
        total_candidates=1,
        processed_candidates=0,
        engine_version="test",
        configuration_snapshot={
            "baseline": BASELINE_CONFIG,
            "simulation": SIM_CONFIG,
            "candidate_ids": [str(alice.id)],
            "job": {"title": "Senior Software Engineer", "location": "Remote", "employment_type": "full_time", "description": "Lead platform engineering with Python."},
        },
    )

    completed = await service.execute(execution.id)
    assert completed.status == "completed"
    again = await service.execute(execution.id)
    assert again.id == completed.id
    rows = await session.execute(
        select(func.count()).select_from(SimulationResult).where(SimulationResult.execution_id == execution.id),
    )
    assert rows.scalar() == 1
    impacts = await session.execute(
        select(func.count()).select_from(SimulationImpact).where(SimulationImpact.execution_id == execution.id),
    )
    assert impacts.scalar() == 9


# ─────────────────────────────────────────────────────────────────────
# 4. Results pagination / filter / sort
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_results_pagination_filter_sort(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Page Org", f"page-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    await _seed_default_pool(session, job)
    scenario = await _create_scenario_via_api(client, token, job, "Pages", SIM_CONFIG)
    await client.post(f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token))

    base_url = f"/api/v1/simulations/{scenario['id']}/results"
    page1 = (await client.get(f"{base_url}?page=1&page_size=2", headers=_auth(token))).json()
    assert page1["total"] == 3
    assert len(page1["items"]) == 2
    page2 = (await client.get(f"{base_url}?page=2&page_size=2", headers=_auth(token))).json()
    assert len(page2["items"]) == 1

    qualified = (await client.get(f"{base_url}?change_filter=qualified", headers=_auth(token))).json()
    assert qualified["total"] == len(
        [r for r in page1["items"] + page2["items"] if r["simulation_status"] == "qualified"],
    )

    improved = (await client.get(
        f"{base_url}?sort_by=score_change&order=desc&page_size=3", headers=_auth(token),
    )).json()
    deltas = [r["score_change"] for r in improved["items"]]
    assert deltas == sorted(deltas, reverse=True)


# ─────────────────────────────────────────────────────────────────────
# 5. RBAC / tenant isolation
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rbac_and_tenant_isolation(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org_a = await _create_org(session, "Tenant A", f"tena-{uuid.uuid4().hex[:6]}")
    recruiter_a, token_a = await _setup_recruiter_with_org(session, client, org_a, email_prefix="ra")
    job = await _create_job(session, recruiter_a, org_a)
    await _seed_default_pool(session, job)
    scenario = await _create_scenario_via_api(client, token_a, job, "Tenant", SIM_CONFIG)
    await client.post(f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token_a))

    org_b = await _create_org(session, "Tenant B", f"tenb-{uuid.uuid4().hex[:6]}")
    recruiter_b, token_b = await _setup_recruiter_with_org(session, client, org_b, email_prefix="rb")

    run_resp = await client.post(
        f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token_b),
    )
    assert run_resp.status_code == 403
    results_resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/results", headers=_auth(token_b),
    )
    assert results_resp.status_code == 403
    summary_resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/summary", headers=_auth(token_b),
    )
    assert summary_resp.status_code == 403

    candidate = User(
        id=uuid.uuid4(), full_name="Cand",
        email=f"cand_{uuid.uuid4().hex[:6]}@test.com", password_hash=hash_password(PASSWORD), is_active=True,
    )
    session.add(candidate)
    await session.flush()
    cand_token = await _login(client, candidate.email)
    denied = await client.get(
        f"/api/v1/simulations/{scenario['id']}/executions", headers=_auth(cand_token),
    )
    assert denied.status_code == 403


# ─────────────────────────────────────────────────────────────────────
# 6. CRITICAL regression — live hiring data is never touched
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_never_modifies_live_hiring_data(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Safe Org", f"safe-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    await _seed_default_pool(session, job)
    scenario = await _create_scenario_via_api(client, token, job, "Safe", SIM_CONFIG)

    job_cols = [
        Job.title, Job.description, Job.location, Job.employment_type,
        Job.required_skills, Job.preferred_skills, Job.experience_required,
        Job.education_required, Job.version, Job.status, Job.salary_min, Job.salary_max,
    ]
    before_job = (
        await session.execute(select(*job_cols).where(Job.id == job.id))
    ).one()
    before_rankings = (
        await session.execute(select(func.count()).select_from(CandidateRanking))
    ).scalar()
    before_screenings = (
        await session.execute(select(func.count()).select_from(ScreeningResult))
    ).scalar()
    before_apps = (
        await session.execute(select(func.count()).select_from(JobApplication).where(JobApplication.job_id == job.id))
    ).scalar()

    run = (await client.post(
        f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token),
    )).json()
    assert run["status"] == "completed"

    after_job = (
        await session.execute(select(*job_cols).where(Job.id == job.id))
    ).one()
    assert before_job == after_job, "Job row was modified by the simulation run!"

    assert (
        await session.execute(select(func.count()).select_from(CandidateRanking))
    ).scalar() == before_rankings, "Simulation created CandidateRanking rows!"
    assert (
        await session.execute(select(func.count()).select_from(ScreeningResult))
    ).scalar() == before_screenings, "Simulation created ScreeningResult rows!"
    assert (
        await session.execute(select(func.count()).select_from(JobApplication).where(JobApplication.job_id == job.id))
    ).scalar() == before_apps, "Simulation touched job applications!"

    results_stored = (
        await session.execute(
            select(func.count()).select_from(SimulationResult).join(
                SimulationExecution, SimulationExecution.id == SimulationResult.execution_id,
            ),
        )
    ).scalar()
    assert results_stored == 3

    audit_events = (await session.execute(
        select(AuditLog.event_type).where(AuditLog.resource_type == "simulation_execution"),
    )).scalars().all()
    assert "simulation_run_started" in audit_events
    assert "simulation_run_completed" in audit_events