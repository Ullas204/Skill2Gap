"""Tests for Simulation Intelligence Phase 1 — scenario management.

Covers:
- Pydantic schema validation (weights bounds, threshold/shortlist, extra keys)
- SimulationRepository CRUD + visibility scoping
- SimulationScenarioService baseline snapshotting, status transitions, audit
- API CRUD / RBAC (admin, hr, recruiter allowed; candidate denied)
- Multi-tenant isolation (cross-organization access is forbidden)
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.enums import EmploymentType, JobStatus, MembershipStatus
from app.domain.models import (
    AuditLog,
    Job,
    Organization,
    OrganizationMembership,
    User,
)
from app.domain.screening_schemas import DEFAULT_WEIGHTS
from app.domain.simulation_models import SimulationScenario
from app.domain.simulation_schemas import (
    SimulationConfiguration,
    SimulationScoringWeights,
    SimulationScenarioCreate,
)

PASSWORD = "Sim@12345"


# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────


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


async def _create_job(
    session: AsyncSession,
    recruiter: User,
    org: Organization | None,
    title: str = "Senior Software Engineer",
) -> Job:
    job = Job(
        recruiter_id=recruiter.id,
        organization_id=org.id if org else None,
        title=title,
        company=org.name if org else "Acme Corporation",
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME.value,
        location="Remote",
        description="Lead platform engineering.",
        required_skills=["Python", "SQL", "FastAPI"],
        preferred_skills=["PostgreSQL", "Docker"],
        experience_required="3 years",
        education_required="Bachelor's degree",
        status=JobStatus.PUBLISHED.value,
    )
    session.add(job)
    await session.flush()
    return job


async def _assign_role(session: AsyncSession, user: User, role_name: str) -> None:
    from app.domain.models import Role, UserRole

    role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    assert role, f"Role {role_name!r} must exist (see conftest DEFAULT_ROLES)"
    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.flush()


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


# ─────────────────────────────────────────────────────────────────────
# 1. Schema validation
# ─────────────────────────────────────────────────────────────────────


def test_weights_must_not_all_be_zero() -> None:
    with pytest.raises(ValidationError):
        SimulationScoringWeights(
            skills=0, experience=0, education=0, projects=0,
            certifications=0, location=0, employment_type=0, semantic=0,
        )


def test_weights_out_of_range_rejected() -> None:
    with pytest.raises(ValidationError):
        SimulationScoringWeights(skills=1.1, experience=0.25, education=0.15, projects=0.20)
    with pytest.raises(ValidationError):
        SimulationScoringWeights(skills=-0.1, experience=0.25, education=0.15, projects=0.20)


def test_threshold_and_shortlist_bounds() -> None:
    with pytest.raises(ValidationError):
        SimulationConfiguration(threshold=101)
    with pytest.raises(ValidationError):
        SimulationConfiguration(threshold=-1)
    with pytest.raises(ValidationError):
        SimulationConfiguration(shortlist_size=0)
    with pytest.raises(ValidationError):
        SimulationConfiguration(shortlist_size=501)


def test_extra_config_keys_rejected() -> None:
    with pytest.raises(ValidationError):
        SimulationConfiguration(
            scoring_weights=SimulationScoringWeights(),
            threshold=70,
            shortlist_size=10,
            bogus_parameter="nope",
        )


def test_default_config_shape() -> None:
    cfg = SimulationConfiguration(requirements={"mandatory_skills": ["Python"]})
    assert cfg.threshold == 70
    assert cfg.shortlist_size == 10
    assert cfg.scoring_weights.skills == 0.40


def test_create_schema_name_is_stripped() -> None:
    scenario = SimulationScenarioCreate(job_id=uuid.uuid4(), name="  Lead Weight Test  ")
    assert scenario.name == "Lead Weight Test"


# ─────────────────────────────────────────────────────────────────────
# 2. Repository level
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_repository_crud_and_org_scoping(session: AsyncSession) -> None:
    from app.repositories.simulation import SimulationRepository

    repo = SimulationRepository(session)

    org_a = await _create_org(session, "Repo Alpha", f"repo-a-{uuid.uuid4().hex[:6]}")
    recruiter = User(
        id=uuid.uuid4(), full_name="Repo Bot", email=f"repo_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="x", is_active=True,
    )
    session.add(recruiter)
    await session.flush()
    job = await _create_job(session, recruiter, org_a)

    created = await repo.create(
        organization_id=org_a.id,
        job_id=job.id,
        created_by=recruiter.id,
        name="Repo Scenario",
        status="draft",
        baseline_config={"source": "job_snapshot"},
        simulation_config={"threshold": 70},
        config_version=1,
    )
    assert created.id

    loaded = await repo.get_with_details(created.id)
    assert loaded is not None and loaded.name == "Repo Scenario"

    by_job = await repo.get_by_job(job.id)
    assert [s.id for s in by_job] == [created.id]

    org_ids = [org_a.id]
    visible = await repo.list_visible(recruiter.id, org_ids)
    assert [s.id for s in visible] == [created.id]
    counts = await repo.count_by_status(recruiter.id, org_ids)
    assert counts.get("draft") == 1

    other_org = await _create_org(session, "Repo Beta", f"repo-b-{uuid.uuid4().hex[:6]}")
    bot2 = User(
        id=uuid.uuid4(), full_name="Repo Bot 2",
        email=f"repo2_{uuid.uuid4().hex[:6]}@test.com", password_hash="x", is_active=True,
    )
    session.add(bot2)
    await session.flush()
    invisible = await repo.list_visible(bot2.id, [other_org.id])
    assert invisible == []

    # Own scenarios stay visible to their creator regardless of org list.
    visible_own = await repo.list_visible(recruiter.id, [other_org.id])
    assert [s.id for s in visible_own] == [created.id]

    await repo.delete(created.id)
    assert await repo.get_with_details(created.id) is None


# ─────────────────────────────────────────────────────────────────────
# 3. Service / API — happy path CRUD + audit
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_scenario_snapshots_baseline_and_audits(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Acme API", f"acme-api-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    resp = await client.post(
        "/api/v1/simulations",
        headers=_auth(token),
        json={"job_id": str(job.id), "name": "Weighted Recruiting Experiment", "description": "Test baseline snapshot"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "draft"
    assert data["name"] == "Weighted Recruiting Experiment"
    assert data["job_id"] == str(job.id)
    assert data["organization_id"] == str(org.id)
    assert data["created_by"] == str(recruiter.id)
    assert data["job_title"] == job.title
    assert data["company"] == org.name
    assert data["created_by_name"] == recruiter.full_name
    assert data["config_version"] == 1
    assert data["metadata"] is None

    baseline = data["baseline_config"]
    assert baseline["source"] == "job_snapshot"
    assert baseline["job_version"] == job.version
    assert baseline["scoring_weights"] == DEFAULT_WEIGHTS.model_dump()
    assert baseline["threshold"] == 70
    assert baseline["shortlist_size"] == 10
    assert baseline["requirements"]["mandatory_skills"] == ["Python", "SQL", "FastAPI"]
    assert baseline["requirements"]["preferred_skills"] == ["PostgreSQL", "Docker"]

    # simulation_config defaults to the baseline configuration shape.
    sim = data["simulation_config"]
    assert sim["threshold"] == baseline["threshold"]
    assert sim["shortlist_size"] == baseline["shortlist_size"]
    assert sim["requirements"]["mandatory_skills"] == baseline["requirements"]["mandatory_skills"]
    assert sim["scoring_weights"] == baseline["scoring_weights"]

    audit = await session.execute(
        select(AuditLog).where(AuditLog.event_type == "simulation_created")
    )
    logs = audit.scalars().all()
    assert any(log.resource_id == data["id"] for log in logs)


@pytest.mark.asyncio
async def test_create_with_explicit_simulation_config(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Config Co", f"config-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    resp = await client.post(
        "/api/v1/simulations",
        headers=_auth(token),
        json={
            "job_id": str(job.id),
            "name": "Aggressive Skills Focus",
            "simulation_config": {
                "scoring_weights": {"skills": 0.8, "experience": 0.1, "education": 0.1, "projects": 0.0},
                "threshold": 85,
                "shortlist_size": 5,
                "requirements": {"mandatory_skills": ["Python"]},
            },
        },
    )
    assert resp.status_code == 201, resp.text
    sim = resp.json()["simulation_config"]
    assert sim["threshold"] == 85
    assert sim["shortlist_size"] == 5
    assert sim["scoring_weights"]["skills"] == 0.8
    assert sim["requirements"]["mandatory_skills"] == ["Python"]


@pytest.mark.asyncio
async def test_list_returns_items_and_stats(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "List Org", f"list-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    for name in ["Sim One", "Sim Two"]:
        resp = await client.post(
            "/api/v1/simulations", headers=_auth(token),
            json={"job_id": str(job.id), "name": name},
        )
        assert resp.status_code == 201, resp.text

    resp = await client.get("/api/v1/simulations", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert len(payload["items"]) == 2
    assert {item["name"] for item in payload["items"]} == {"Sim One", "Sim Two"}
    assert payload["stats"]["total"] == 2
    assert payload["stats"]["drafts"] == 2
    assert payload["items"][0]["job_title"] == job.title
    assert payload["items"][0]["created_by_name"] == recruiter.full_name


@pytest.mark.asyncio
async def test_get_returns_full_details(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Detail Org", f"detail-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Detail Sim", "metadata": {"owner": "recruiting"}},
    )).json()

    resp = await client.get(f"/api/v1/simulations/{created['id']}", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == created["id"]
    assert data["metadata"] == {"owner": "recruiting"}
    assert data["baseline_config"]["source"] == "job_snapshot"

    status_resp = await client.get(f"/api/v1/simulations/{created['id']}/status", headers=_auth(token))
    assert status_resp.status_code == 200, status_resp.text
    assert status_resp.json()["status"] == "draft"
    assert status_resp.json()["can_edit"] is True


@pytest.mark.asyncio
async def test_patch_updates_fields_and_config_version(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Patch Org", f"patch-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Before Patch"},
    )).json()
    sim_id = created["id"]

    resp = await client.patch(
        f"/api/v1/simulations/{sim_id}", headers=_auth(token),
        json={
            "name": "After Patch",
            "description": "Edited description",
            "simulation_config": {"threshold": 90},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["name"] == "After Patch"
    assert data["description"] == "Edited description"
    assert data["simulation_config"]["threshold"] == 90
    assert data["config_version"] == 2

    audit = await session.execute(
        select(AuditLog).where(
            AuditLog.event_type == "simulation_updated",
            AuditLog.resource_id == sim_id,
        )
    )
    assert len(audit.scalars().all()) == 1


@pytest.mark.asyncio
async def test_status_transitions_via_api(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Flow Org", f"flow-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Flow Sim"},
    )).json()
    sim_id = created["id"]

    # draft -> ready
    resp = await client.patch(
        f"/api/v1/simulations/{sim_id}", headers=_auth(token), json={"status": "ready"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ready"

    # Execution states are reserved for the engine (Phase 1 manual transitions).
    resp = await client.patch(
        f"/api/v1/simulations/{sim_id}", headers=_auth(token), json={"status": "running"},
    )
    assert resp.status_code == 422, resp.text

    # A READY scenario is no longer editable through the API.
    resp = await client.patch(
        f"/api/v1/simulations/{sim_id}", headers=_auth(token), json={"name": "Nope"},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_delete_simulation(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Del Org", f"del-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Delete Me"},
    )).json()

    resp = await client.delete(f"/api/v1/simulations/{created['id']}", headers=_auth(token))
    assert resp.status_code == 204

    resp = await client.get(f"/api/v1/simulations/{created['id']}", headers=_auth(token))
    assert resp.status_code == 404

    audit = await session.execute(
        select(AuditLog).where(
            AuditLog.event_type == "simulation_deleted",
            AuditLog.resource_id == created["id"],
        )
    )
    assert len(audit.scalars().all()) == 1


# ─────────────────────────────────────────────────────────────────────
# 4. RBAC — who may access
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("role_name", ["admin", "super_admin", "hr", "hr_manager", "recruiter", "organization_admin"])
async def test_allowed_roles_can_list(session: AsyncSession, client: AsyncClient, role_name: str) -> None:
    user = User(
        id=uuid.uuid4(),
        full_name="Allowed User",
        email=f"allowed_{role_name}_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password(PASSWORD),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    from app.domain.models import Role, UserRole
    role = (await session.execute(select(Role).where(Role.name == role_name))).scalar_one_or_none()
    assert role
    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.commit()

    token = await _login(client, user.email)
    resp = await client.get("/api/v1/simulations", headers=_auth(token))
    assert resp.status_code == 200, resp.text


@pytest.mark.asyncio
async def test_candidate_forbidden(session: AsyncSession, client: AsyncClient) -> None:
    from app.domain.models import Role, UserRole
    user = User(
        id=uuid.uuid4(), full_name="Candidate User",
        email=f"cand_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password(PASSWORD), is_active=True,
    )
    session.add(user)
    await session.flush()
    role = (await session.execute(select(Role).where(Role.name == "candidate"))).scalar_one_or_none()
    assert role
    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.commit()

    token = await _login(client, user.email)
    resp = await client.get("/api/v1/simulations", headers=_auth(token))
    assert resp.status_code == 403
    resp = await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(uuid.uuid4()), "name": "Nope"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_missing_or_invalid_auth(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/simulations")
    assert resp.status_code == 422

    resp = await client.get(
        "/api/v1/simulations", headers={"Authorization": "Bearer not-a-real-token"},
    )
    assert resp.status_code == 401


# ─────────────────────────────────────────────────────────────────────
# 5. Multi-tenant isolation
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_org_b_cannot_see_or_touch_org_a_simulations(session: AsyncSession, client: AsyncClient) -> None:
    org_a = await _create_org(session, "Org A", f"orga-{uuid.uuid4().hex[:6]}")
    org_b = await _create_org(session, "Org B", f"orgb-{uuid.uuid4().hex[:6]}")

    recruiter_a, token_a = await _setup_recruiter_with_org(session, client, org_a)
    recruiter_b, token_b = await _setup_recruiter_with_org(session, client, org_b, email_prefix="recruiter_b")

    job_a = await _create_job(session, recruiter_a, org_a)
    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token_a),
        json={"job_id": str(job_a.id), "name": "Tenant A Sim"},
    )).json()

    # Not visible in B's list...
    resp = await client.get("/api/v1/simulations", headers=_auth(token_b))
    assert resp.status_code == 200
    assert all(item["id"] != created["id"] for item in resp.json()["items"])

    # ...not readable directly...
    resp = await client.get(f"/api/v1/simulations/{created['id']}", headers=_auth(token_b))
    assert resp.status_code == 403

    # ...and B cannot create a simulation against A's job.
    resp = await client.post(
        "/api/v1/simulations", headers=_auth(token_b),
        json={"job_id": str(job_a.id), "name": "Cross Tenant Attempt"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_org_less_job_only_accessible_to_creator(session: AsyncSession, client: AsyncClient) -> None:
    org_b = await _create_org(session, "Org B2", f"orgb2-{uuid.uuid4().hex[:6]}")
    owner = User(
        id=uuid.uuid4(), full_name="Job Owner",
        email=f"owner_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password(PASSWORD), is_active=True,
    )
    session.add(owner)
    await session.flush()
    await _assign_role(session, owner, "recruiter")
    token_owner = await _login(client, owner.email)
    job = await _create_job(session, owner, org=None)

    recruiter_b, token_b = await _setup_recruiter_with_org(session, client, org_b)

    # Creator can create a simulation for their own org-less job.
    resp = await client.post(
        "/api/v1/simulations", headers=_auth(token_owner),
        json={"job_id": str(job.id), "name": "Owner Sim", "description": "Org-less job"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["organization_id"] is None

    # A member of another org cannot target that job.
    resp = await client.post(
        "/api/v1/simulations", headers=_auth(token_b),
        json={"job_id": str(job.id), "name": "Not Yours"},
    )
    assert resp.status_code == 403

    # The other recruiter cannot read the owner's scenario either.
    owner_list = (await client.get("/api/v1/simulations", headers=_auth(token_owner))).json()
    created_id = owner_list["items"][0]["id"]
    resp = await client.get(f"/api/v1/simulations/{created_id}", headers=_auth(token_b))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_hr_member_of_org_can_modify_but_outsider_cannot(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Shared Org", f"shared-{uuid.uuid4().hex[:6]}")
    recruiter, token_recruiter = await _setup_recruiter_with_org(session, client, org)
    hr = User(
        id=uuid.uuid4(), full_name="Org HR", email=f"sharedhr_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password(PASSWORD), is_active=True,
    )
    session.add(hr)
    await session.flush()
    await _assign_role(session, hr, "hr_manager")
    await _add_membership(session, hr, org, "hr_manager")
    token_hr = await _login(client, hr.email)

    orger = await _create_org(session, "Elsewhere", f"else-{uuid.uuid4().hex[:6]}")
    outsider, token_out = await _setup_recruiter_with_org(session, client, orger, email_prefix="outsider")

    job = await _create_job(session, recruiter, org)
    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token_recruiter),
        json={"job_id": str(job.id), "name": "Shared Work"},
    )).json()

    # Same-org HR may update.
    resp = await client.patch(
        f"/api/v1/simulations/{created['id']}", headers=_auth(token_hr),
        json={"name": "HR Renamed"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "HR Renamed"

    # Member of a different org may not.
    resp = await client.patch(
        f"/api/v1/simulations/{created['id']}", headers=_auth(token_out),
        json={"name": "Hijack"},
    )
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────
# 6. Unknown job handling
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_for_missing_job_is_404(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "NoJob Org", f"nojob-{uuid.uuid4().hex[:6]}")
    _, token = await _setup_recruiter_with_org(session, client, org)
    resp = await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(uuid.uuid4()), "name": "Ghost Job"},
    )
    assert resp.status_code == 404