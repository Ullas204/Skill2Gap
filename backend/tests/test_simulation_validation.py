"""Tests for Simulation Intelligence Phase 2 — Scenario Builder.

Covers:
- SimulationConfigurationValidator: weights must total 100%, skill
  duplicates/overlap/empties, experience range bounds, education level &
  requirement, threshold/shortlist.
- Change detection: baseline-vs-scenario diff with +/- indicators, skill
  movement, structured experience/education labels.
- API: POST /simulations/{id}/validate, GET /simulations/{id}/changes,
  the `ready` validation gate, config versioning, audit events, RBAC and
  multi-tenant isolation.
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
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
from app.domain.simulation_schemas import SimulationConfiguration
from app.services.simulation.change_detection import compute_changes
from app.services.simulation.configuration_validator import (
    SimulationConfigurationValidator,
    normalize_skill,
)

PASSWORD = "Sim@12345"

VALID_CONFIG = {
    "scoring_weights": {
        "skills": 0.40, "experience": 0.25, "education": 0.15, "projects": 0.20,
        "certifications": 0.0, "location": 0.0, "employment_type": 0.0, "semantic": 0.0,
    },
    "threshold": 70,
    "shortlist_size": 10,
    "requirements": {
        "mandatory_skills": ["Python", "SQL"],
        "preferred_skills": ["Docker"],
        "experience": {"minimum_years": 3, "maximum_years": None},
        "education": {"level": "bachelor", "requirement": "required"},
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
    org: Organization | None,
    title: str = "Data Engineer",
) -> Job:
    job = Job(
        recruiter_id=recruiter.id,
        organization_id=org.id if org else None,
        title=title,
        company=org.name if org else "Acme Corporation",
        department="Data",
        employment_type=EmploymentType.FULL_TIME.value,
        location="Remote",
        description="Build data pipelines.",
        required_skills=["Python", "SQL"],
        preferred_skills=["Docker"],
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
    email_prefix: str = "builder",
) -> tuple[User, str]:
    user = User(
        id=uuid.uuid4(),
        full_name="Builder Recruiter",
        email=f"{email_prefix}_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password(PASSWORD),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    await _assign_role(session, user, "recruiter")
    await _add_membership(session, user, org, "recruiter")
    await session.commit()
    token = await _login(client, user.email)
    return user, token


# ─────────────────────────────────────────────────────────────────────
# 1. Configuration validator (unit)
# ─────────────────────────────────────────────────────────────────────


def _errors(config: dict | None) -> dict[str, str]:
    valid, issues = SimulationConfigurationValidator.validate(config)
    return valid, {issue.field: issue.message for issue in issues}


def test_valid_config_passes() -> None:
    valid, errors = _errors(VALID_CONFIG)
    assert valid is True
    assert errors == {}


def test_none_config_is_invalid() -> None:
    valid, errors = _errors(None)
    assert valid is False
    assert "config" in errors


def test_weights_must_total_100_percent() -> None:
    config = {**VALID_CONFIG}
    config["scoring_weights"] = {
        **VALID_CONFIG["scoring_weights"], "skills": 0.75, "experience": 0.50,
    }
    valid, errors = _errors(config)
    assert valid is False
    assert "scoring_weights.total" in errors
    assert "total" in errors["scoring_weights.total"].lower()


def test_weight_out_of_bounds_reported_per_dimension() -> None:
    config = {**VALID_CONFIG}
    config["scoring_weights"] = {**VALID_CONFIG["scoring_weights"], "skills": 1.5}
    valid, errors = _errors(config)
    assert valid is False
    assert "scoring_weights.skills" in errors


def test_missing_scoring_weights() -> None:
    config = {**VALID_CONFIG}
    del config["scoring_weights"]
    valid, errors = _errors(config)
    assert valid is False
    assert "scoring_weights" in errors


def test_duplicate_skills_rejected() -> None:
    config = {**VALID_CONFIG}
    config["requirements"] = {
        **VALID_CONFIG["requirements"],
        "mandatory_skills": ["Python", "  python "],
    }
    valid, errors = _errors(config)
    assert valid is False
    assert any("uplicated" in msg and "Python" in msg for msg in errors.values())


def test_mandatory_preferred_overlap_rejected() -> None:
    config = {**VALID_CONFIG}
    config["requirements"] = {
        **VALID_CONFIG["requirements"],
        "preferred_skills": ["SQL"],
    }
    valid, errors = _errors(config)
    assert valid is False
    assert "requirements" in errors and "both mandatory and preferred" in errors["requirements"]


def test_empty_skill_rejected() -> None:
    config = {**VALID_CONFIG}
    config["requirements"] = {**VALID_CONFIG["requirements"], "mandatory_skills": ["   "]}
    valid, errors = _errors(config)
    assert valid is False
    assert "requirements.mandatory_skills" in errors


def test_experience_max_below_min_rejected() -> None:
    config = {**VALID_CONFIG}
    config["requirements"] = {
        **VALID_CONFIG["requirements"],
        "experience": {"minimum_years": 5, "maximum_years": 3},
    }
    valid, errors = _errors(config)
    assert valid is False
    assert "requirements.experience" in errors


def test_experience_negative_rejected() -> None:
    config = {**VALID_CONFIG}
    config["requirements"] = {
        **VALID_CONFIG["requirements"],
        "experience": {"minimum_years": -1, "maximum_years": None},
    }
    valid, errors = _errors(config)
    assert valid is False
    assert "requirements.experience.minimum_years" in errors


def test_experience_with_no_bounds_rejected() -> None:
    config = {**VALID_CONFIG}
    config["requirements"] = {
        **VALID_CONFIG["requirements"],
        "experience": {"minimum_years": None, "maximum_years": None},
    }
    valid, errors = _errors(config)
    assert valid is False
    assert "requirements.experience" in errors


def test_education_unknown_level_rejected() -> None:
    config = {**VALID_CONFIG}
    config["requirements"] = {
        **VALID_CONFIG["requirements"],
        "education": {"level": "astronaut", "requirement": "required"},
    }
    valid, errors = _errors(config)
    assert valid is False
    assert "requirements.education.level" in errors


def test_education_unknown_requirement_rejected() -> None:
    config = {**VALID_CONFIG}
    config["requirements"] = {
        **VALID_CONFIG["requirements"],
        "education": {"level": "master", "requirement": "mandatory"},
    }
    valid, errors = _errors(config)
    assert valid is False
    assert "requirements.education.requirement" in errors


def test_education_any_level_is_valid() -> None:
    config = {**VALID_CONFIG}
    config["requirements"] = {
        **VALID_CONFIG["requirements"],
        "education": {"level": None, "requirement": "optional"},
    }
    valid, errors = _errors(config)
    assert valid is True, errors


def test_normalize_skill_canonicalizes_aliases() -> None:
    assert normalize_skill("PostgreSQL") == "postgresql"
    assert normalize_skill("  React.js  ") == "react"
    assert normalize_skill("   ") == ""
    assert normalize_skill("Kubernetes") == "kubernetes"


# ─────────────────────────────────────────────────────────────────────
# 2. Change detection (unit)
# ─────────────────────────────────────────────────────────────────────


def _baseline() -> dict:
    return {
        "scoring_weights": {
            "skills": 0.30, "experience": 0.20, "education": 0.15, "projects": 0.10,
            "certifications": 0.10, "location": 0.05, "employment_type": 0.05, "semantic": 0.05,
        },
        "threshold": 70,
        "shortlist_size": 10,
        "requirements": {
            "mandatory_skills": ["Python", "SQL"],
            "preferred_skills": ["Docker"],
            "experience_required": "3 years",
            "education_required": "Bachelor's degree",
        },
    }


def test_no_changes_reports_all_unchanged() -> None:
    baseline = _baseline()
    scenario = {**baseline}
    changes = compute_changes(uuid.uuid4(), 1, baseline, scenario)
    assert changes.total_changes == 0
    assert changes.changed_fields == []
    assert all(f.change == "unchanged" for f in changes.fields)


def test_weight_and_threshold_changes_detected() -> None:
    baseline = _baseline()
    scenario = {**baseline}
    scenario["scoring_weights"] = {**baseline["scoring_weights"], "skills": 0.45, "experience": 0.10}
    scenario["threshold"] = 85
    changes = compute_changes(uuid.uuid4(), 2, baseline, scenario)

    by_key = {f.key: f for f in changes.fields}
    assert by_key["scoring_weights.skills"].change == "increased"
    assert by_key["scoring_weights.experience"].change == "decreased"
    assert by_key["scoring_weights.projects"].change == "unchanged"
    assert by_key["threshold"].change == "increased"
    assert "threshold" in changes.changed_fields
    assert changes.total_changes == 3


def test_skill_added_and_removed() -> None:
    baseline = _baseline()
    scenario = {**baseline}
    scenario["requirements"] = {
        **baseline["requirements"],
        "mandatory_skills": ["Python", "PostgreSQL"],
        "preferred_skills": ["Docker", "Airflow"],
    }
    changes = compute_changes(uuid.uuid4(), 1, baseline, scenario)
    assert changes.skills.mandatory_added == ["PostgreSQL"]
    assert changes.skills.preferred_added == ["Airflow"]
    assert changes.skills.mandatory_removed == ["SQL"]
    assert changes.skills.moved == []
    assert "requirements.mandatory_skills" in changes.changed_fields


def test_skill_moved_between_lists() -> None:
    baseline = _baseline()
    scenario = {**baseline}
    scenario["requirements"] = {
        **baseline["requirements"],
        "mandatory_skills": ["Python"],
        "preferred_skills": ["Docker", "SQL"],
    }
    changes = compute_changes(uuid.uuid4(), 1, baseline, scenario)
    moved = changes.skills.moved
    assert any(m.skill == "SQL" and m.from_list == "mandatory" and m.to_list == "preferred" for m in moved)


def test_skill_moved_preferred_to_mandatory() -> None:
    baseline = _baseline()
    scenario = {**baseline}
    scenario["requirements"] = {
        **baseline["requirements"],
        "mandatory_skills": ["Python", "SQL", "Docker"],
        "preferred_skills": [],
    }
    changes = compute_changes(uuid.uuid4(), 1, baseline, scenario)
    assert any(m.skill == "Docker" and m.from_list == "preferred" and m.to_list == "mandatory" for m in changes.skills.moved)


def test_structured_experience_and_education_diffs() -> None:
    baseline = _baseline()
    scenario = {**baseline}
    scenario["requirements"] = {
        **baseline["requirements"],
        "experience": {"minimum_years": 3, "maximum_years": 5},
        "education": {"level": "master", "requirement": "preferred"},
    }
    changes = compute_changes(uuid.uuid4(), 1, baseline, scenario)
    by_key = {f.key: f for f in changes.fields}
    assert by_key["requirements.experience"].baseline == "3 years"
    assert by_key["requirements.experience"].scenario == "3–5 years"
    assert by_key["requirements.experience"].change == "changed"
    assert by_key["requirements.education"].scenario == "Master's (Preferred)"
    assert by_key["requirements.education"].change == "changed"


def test_skill_alias_is_not_flagged_as_change() -> None:
    baseline = _baseline()
    scenario = {**baseline}
    scenario["requirements"] = {
        **baseline["requirements"],
        "preferred_skills": ["docker"],
        "experience": {"minimum_years": 3, "maximum_years": None},
    }
    changes = compute_changes(uuid.uuid4(), 1, baseline, scenario)
    assert changes.skills.preferred_added == []
    assert changes.skills.preferred_removed == []
    assert changes.changed_fields == ["requirements.experience"]


# ─────────────────────────────────────────────────────────────────────
# 3. Service / API — validate & changes
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_valid_scenario_validates(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Valid Org", f"valid-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Valid One"},
    )).json()

    resp = await client.post(f"/api/v1/simulations/{created['id']}/validate", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["valid"] is True
    assert resp.json()["errors"] == []


@pytest.mark.asyncio
async def test_invalid_config_validation_reports_structured_errors(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Bad Org", f"bad-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    config = {
        **VALID_CONFIG,
        "scoring_weights": {**VALID_CONFIG["scoring_weights"], "skills": 0.75, "experience": 0.50},
    }
    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Bad Weights", "simulation_config": config},
    )).json()

    resp = await client.post(f"/api/v1/simulations/{created['id']}/validate", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["valid"] is False
    fields = {issue["field"] for issue in payload["errors"]}
    assert "scoring_weights.total" in fields


@pytest.mark.asyncio
async def test_changes_endpoint_reports_diff(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Diff Org", f"diff-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Diff Me"},
    )).json()
    sim_id = created["id"]

    resp = await client.get(f"/api/v1/simulations/{sim_id}/changes", headers=_auth(token))
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["simulation_id"] == sim_id
    assert payload["total_changes"] == 0
    assert len(payload["fields"]) == 12  # 8 weights + threshold + shortlist + experience + education

    # After editing, the diff reflects the change.
    (await client.patch(
        f"/api/v1/simulations/{sim_id}", headers=_auth(token),
        json={"simulation_config": {**VALID_CONFIG, "threshold": 88}},
    )).json()
    resp = await client.get(f"/api/v1/simulations/{sim_id}/changes", headers=_auth(token))
    payload = resp.json()
    assert payload["total_changes"] >= 1
    threshold = next(f for f in payload["fields"] if f["key"] == "threshold")
    assert threshold["change"] == "increased"
    assert threshold["scenario"] == 88
    assert "threshold" in payload["changed_fields"]


@pytest.mark.asyncio
async def test_config_version_embedded_and_incremented(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Version Org", f"ver-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Versioned"},
    )).json()
    assert created["config_version"] == 1
    assert created["simulation_config"]["version"] == 1

    updated = (await client.patch(
        f"/api/v1/simulations/{created['id']}", headers=_auth(token),
        json={"simulation_config": {"threshold": 80}},
    )).json()
    assert updated["config_version"] == 2
    assert updated["simulation_config"]["version"] == 2


@pytest.mark.asyncio
async def test_mark_ready_blocked_when_invalid_then_allowed(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Gate Org", f"gate-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    bad_config = {
        **VALID_CONFIG,
        "scoring_weights": {**VALID_CONFIG["scoring_weights"], "skills": 0.9, "education": 0.3},
        "requirements": {
            **VALID_CONFIG["requirements"],
            "preferred_skills": ["Python"],
        },
    }
    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Gatekeeper", "simulation_config": bad_config},
    )).json()
    sim_id = created["id"]

    # Invalid config: promotion is rejected with 422 and structured extra data.
    resp = await client.patch(
        f"/api/v1/simulations/{sim_id}", headers=_auth(token), json={"status": "ready"},
    )
    assert resp.status_code == 422, resp.text
    payload = resp.json()
    assert payload["code"] == "validation_error"
    assert "validation_errors" in payload.get("extra", {})
    # The scenario is still a draft — promotion did not happen.
    assert (await client.get(f"/api/v1/simulations/{sim_id}", headers=_auth(token))).json()["status"] == "draft"

    # Fix the config and promote in one call.
    resp = await client.patch(
        f"/api/v1/simulations/{sim_id}", headers=_auth(token),
        json={"simulation_config": VALID_CONFIG, "status": "ready"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_ready_scenario_config_is_frozen(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Frozen Org", f"frozen-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Frozen"},
    )).json()
    (await client.patch(
        f"/api/v1/simulations/{created['id']}", headers=_auth(token), json={"status": "ready"},
    )).json()

    resp = await client.patch(
        f"/api/v1/simulations/{created['id']}", headers=_auth(token),
        json={"simulation_config": {"threshold": 95}},
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_audit_events_for_validate_and_status_change(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Audit Org", f"audit-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)

    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Audit Me"},
    )).json()
    sim_id = created["id"]

    await client.post(f"/api/v1/simulations/{sim_id}/validate", headers=_auth(token))
    validate_logs = (await session.execute(
        select(AuditLog).where(
            AuditLog.event_type == "simulation_validated",
            AuditLog.resource_id == sim_id,
        ),
    )).scalars().all()
    assert len(validate_logs) == 1
    assert validate_logs[0].success is True

    (await client.patch(
        f"/api/v1/simulations/{sim_id}", headers=_auth(token), json={"status": "ready"},
    )).json()
    status_logs = (await session.execute(
        select(AuditLog).where(
            AuditLog.event_type == "simulation_status_changed",
            AuditLog.resource_id == sim_id,
        ),
    )).scalars().all()
    assert len(status_logs) == 1
    assert status_logs[0].details.get("status") == "ready"


@pytest.mark.asyncio
async def test_candidate_forbidden_on_validate_and_changes(session: AsyncSession, client: AsyncClient) -> None:
    org = await _create_org(session, "Cand Org", f"cand-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org, title="Cand Target")
    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token),
        json={"job_id": str(job.id), "name": "Candidate Gate"},
    )).json()

    user = User(
        id=uuid.uuid4(), full_name="Candidate",
        email=f"candgate_{uuid.uuid4().hex[:6]}@test.com",
        password_hash=hash_password(PASSWORD), is_active=True,
    )
    session.add(user)
    await session.flush()
    await _assign_role(session, user, "candidate")
    await session.commit()
    cand_token = await _login(client, user.email)

    assert (await client.post(
        f"/api/v1/simulations/{created['id']}/validate", headers=_auth(cand_token),
    )).status_code == 403
    assert (await client.get(
        f"/api/v1/simulations/{created['id']}/changes", headers=_auth(cand_token),
    )).status_code == 403


@pytest.mark.asyncio
async def test_cross_org_validate_and_changes_forbidden(session: AsyncSession, client: AsyncClient) -> None:
    org_a = await _create_org(session, "Tenant A", f"ta-{uuid.uuid4().hex[:6]}")
    org_b = await _create_org(session, "Tenant B", f"tb-{uuid.uuid4().hex[:6]}")
    recruiter_a, token_a = await _setup_recruiter_with_org(session, client, org_a, email_prefix="tenant_a")
    recruiter_b, token_b = await _setup_recruiter_with_org(session, client, org_b, email_prefix="tenant_b")

    job_a = await _create_job(session, recruiter_a, org_a)
    created = (await client.post(
        "/api/v1/simulations", headers=_auth(token_a),
        json={"job_id": str(job_a.id), "name": "Tenant A Sim"},
    )).json()

    assert (await client.post(
        f"/api/v1/simulations/{created['id']}/validate", headers=_auth(token_b),
    )).status_code == 403
    assert (await client.get(
        f"/api/v1/simulations/{created['id']}/changes", headers=_auth(token_b),
    )).status_code == 403


@pytest.mark.asyncio
async def test_pydantic_schema_accepts_structured_requirements() -> None:
    cfg = SimulationConfiguration(
        scoring_weights={
            "skills": 0.4, "experience": 0.25, "education": 0.15, "projects": 0.2,
            "certifications": 0, "location": 0, "employment_type": 0, "semantic": 0,
        },
        requirements={
            "mandatory_skills": ["Python"],
            "preferred_skills": [],
            "experience": {"minimum_years": 3, "maximum_years": 5},
            "education": {"level": "master", "requirement": "preferred"},
        },
    )
    assert cfg.version == 1
    assert cfg.requirements.experience.minimum_years == 3
    assert cfg.requirements.education.level == "master"
    assert cfg.requirements.education.requirement == "preferred"

    import pytest as _pytest
    from pydantic import ValidationError as _ValidationError

    with _pytest.raises(_ValidationError):
        SimulationConfiguration(
            requirements={"education": {"level": "phd", "requirement": "required"}},
        )
    with _pytest.raises(_ValidationError):
        SimulationConfiguration(
            requirements={"experience": {"minimum_years": 6, "maximum_years": 2}},
        )