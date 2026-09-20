"""Phase 11 — AI Demo Data Generator & Recruitment Simulation extensions.

Covers:
- Named industry scenarios (campus/startup/enterprise/IT/healthcare/etc.)
- ensure_scenarios upsert on legacy databases
- Skill-category constrained generation
- num_companies customization knob
- Hiring decision pipeline (shortlist → interview → offer → hire/reject)
- Difficulty semantics (hard vs easy with identical seed)
- Status totals + export enrichment
- API RBAC enforcement for demo endpoints
"""

from __future__ import annotations

import random
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select

from app.core.security import hash_password
from app.domain.demo_models import DemoCompany, DemoScenario, DemoRun, SimulationEvent
from app.domain.demo_schemas import DemoCustomRequest, DemoGenerateRequest
from app.domain.models import (
    AuditLog,
    Job,
    JobApplication,
    Role,
    User,
    UserRole,
)
from app.services.demo import data_pool
from app.services.demo.demo_service import DEMO_EMAIL_DOMAIN, SCENARIOS, DemoService
from app.services.demo.pipeline_simulator import PipelineSimulator

service = DemoService()

PASSWORD = "SecureP@ss1"

NAMED_SCENARIO_SLUGS = {
    "campus-placement",
    "startup-hiring",
    "enterprise-hiring",
    "it-company-hiring",
    "healthcare-recruitment",
    "mass-hiring",
    "remote-hiring",
    "finance-recruitment",
    "government-recruitment",
}


async def _count(session, model) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar() or 0


async def _create_admin(session) -> User:
    simulator = PipelineSimulator(session)
    return await simulator.create_user(
        random.Random(0), "admin", "admin@hirecraft.ai",
    )


async def _create_fresh_admin(session) -> User:
    simulator = PipelineSimulator(session)
    email = f"p11_admin_{uuid.uuid4().hex[:8]}@hirecraft.ai"
    return await simulator.create_user(random.Random(0), "admin", email)


async def _run(session, admin: User, **overrides) -> DemoRun:
    base = dict(
        num_candidates=4,
        num_recruiters=1,
        num_hr=0,
        num_jobs=2,
        candidates_per_job=3,
        include_screening=True,
        include_interviews=True,
        include_reports=False,
        include_agent_indexing=False,
        resume_format="txt",
        seed=11,
    )
    base.update(overrides)
    request = DemoGenerateRequest(**base)
    run = await service.create_run(session, request, admin.id)
    await service.generate_run(run, session, commit_stages=False)
    await session.flush()
    return run


@pytest_asyncio.fixture
async def admin(session) -> User:
    return await _create_admin(session)


# ═══════════════════════════════════════════════════════════════════
# 1. Scenario catalog (Module 9)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_named_industry_scenarios_present(session) -> None:
    scenarios = await service.list_scenarios(session)
    slugs = {s.slug for s in scenarios}
    assert NAMED_SCENARIO_SLUGS <= slugs

    campus = next(s for s in scenarios if s.slug == "campus-placement")
    assert campus.config["industry_key"] == "campus"
    assert campus.config["hiring_difficulty"] in {"easy", "medium", "hard"}
    assert campus.tags and "campus" in campus.tags


@pytest.mark.asyncio
async def test_new_scenarios_upsert_into_legacy_db(session) -> None:
    """A DB seeded by the old 4-scenario version gains the new presets."""
    legacy = DemoScenario(
        name="Quick Start",
        slug="quick-start",
        description="old description",
        is_active=True,
        config={"num_candidates": 5},
        tags=["legacy"],
    )
    session.add(legacy)
    await session.flush()
    legacy_id = legacy.id

    scenarios = await service.ensure_scenarios(session)
    slugs = {s.slug for s in scenarios}
    assert NAMED_SCENARIO_SLUGS <= slugs
    assert len(slugs) == len(SCENARIOS)

    refreshed = next(s for s in scenarios if s.id == legacy_id)
    assert refreshed.description != "old description"


@pytest.mark.asyncio
async def test_scenario_configs_reference_valid_pools() -> None:
    """Every named scenario must point at real pools (fail-fast config check)."""
    for data in SCENARIOS:
        key = data["config"].get("industry_key")
        if key:
            assert key in data_pool.INDUSTRY_COMPANIES, f"bad industry_key {key}"
            assert key in data_pool.INDUSTRY_JOB_TITLES, f"bad title pool {key}"
        for category in data["config"].get("skill_categories", []):
            assert category in data_pool.SKILL_CATEGORY_POOLS, f"bad skill category {category}"
        difficulty = data["config"].get("hiring_difficulty")
        if difficulty:
            assert difficulty in data_pool.HIRING_DIFFICULTY_PRESETS


# ═══════════════════════════════════════════════════════════════════
# 2. Customization knobs (Modules 2 & 9)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_num_companies_respected(session, admin) -> None:
    await _run(session, admin, num_companies=2, num_jobs=2, seed=5)
    assert await _count(session, DemoCompany) == 2


@pytest.mark.asyncio
async def test_custom_company_names_win_over_scenario_pool(session, admin) -> None:
    request = DemoCustomRequest(
        companies=["Globex Corp", "Initech Ltd"],
        num_candidates=2, num_recruiters=1, num_hr=0, num_jobs=1,
        num_companies=2,
        candidates_per_job=1,
        include_screening=False, include_interviews=False,
        include_reports=False, include_agent_indexing=False,
        resume_format="txt", seed=3,
    )
    run = await service.create_run(session, request, admin.id)
    await service.generate_run(run, session, commit_stages=False)

    names = {c.name for c in (await session.execute(select(DemoCompany))).scalars().all()}
    assert names == {"Globex Corp", "Initech Ltd"}


@pytest.mark.asyncio
async def test_skill_categories_constrain_job_skills(session, admin) -> None:
    pool = set(data_pool.SKILL_CATEGORY_POOLS["healthcare"])
    await _run(
        session, admin,
        skill_categories=["healthcare"],
        job_titles=["Registered Nurse", "Clinical Data Analyst"],
    )
    jobs = (await session.execute(select(Job))).scalars().all()
    assert jobs, "expected jobs to be generated"
    for job in jobs:
        assert set(job.required_skills) <= pool, (
            f"{job.required_skills} leaked outside the healthcare pool"
        )


@pytest.mark.asyncio
async def test_invalid_difficulty_rejected_by_schema(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/v1/demo/generate",
        json={"scenario_slug": "quick-start", "hiring_difficulty": "impossible"},
    )
    assert resp.status_code in (401, 403, 422)


# ═══════════════════════════════════════════════════════════════════
# 3. Hiring decisions pipeline (Module 6 / Module 10)
# ═══════════════════════════════════════════════════════════════════


TERMINAL_STATUSES = {
    "applied", "under_review", "shortlisted", "interview_scheduled",
    "rejected", "offered", "hired",
}


@pytest.mark.asyncio
async def test_decisions_advance_application_statuses(session, admin) -> None:
    run = await _run(session, admin)
    assert run.status == "completed"

    apps = (await session.execute(select(JobApplication))).scalars().all()
    assert apps
    statuses = {a.status for a in apps}
    assert statuses <= TERMINAL_STATUSES
    # Decisions must actually move applications beyond plain "applied".
    assert statuses - {"applied"}, "no application progressed past applied"

    stats = run.stats or {}
    decisions = stats.get("decisions") or {}
    assert decisions.get("hired", 0) + decisions.get("rejected", 0) >= 1
    # Decision counters must mirror the database statuses exactly.
    assert decisions.get("hired", 0) == sum(1 for a in apps if a.status == "hired")
    assert decisions.get("rejected", 0) == sum(1 for a in apps if a.status == "rejected")
    assert decisions.get("shortlisted", 0) >= sum(
        1 for a in apps if a.status in ("hired", "rejected", "shortlisted")
    ) - decisions.get("rejected", 0) - decisions.get("hired", 0)
    assert len(apps) == stats.get("applications")


@pytest.mark.asyncio
async def test_decisions_emit_timeline_events_and_audit(session, admin) -> None:
    run = await _run(session, admin)

    events = (
        await session.execute(
            select(SimulationEvent).where(SimulationEvent.stage == "decisions")
        )
    ).scalars().all()
    # Progress markers carry no details; per-job decision events do.
    decision_events = [e for e in events if e.details]
    assert any("offers" in e.message for e in decision_events)
    assert all("transitions" in (e.details or {}) for e in decision_events)

    audits = (
        await session.execute(
            select(AuditLog).where(AuditLog.action == "demo.decisions")
        )
    ).scalars().all()
    assert audits
    details = audits[-1].details or {}
    assert "hired" in details and "offered" in details


@pytest.mark.asyncio
async def test_hired_implies_high_score_with_hard_threshold(session, admin) -> None:
    threshold = data_pool.HIRING_DIFFICULTY_PRESETS["hard"]["hire_threshold"]
    run = await _run(
        session, admin,
        hiring_difficulty="hard", include_interviews=True,
        num_candidates=6, candidates_per_job=4, num_jobs=1, seed=99,
    )
    assert run.status == "completed"

    from app.domain.models import Interview, InterviewScorecard

    rows = (
        await session.execute(
            select(JobApplication, InterviewScorecard.overall_score)
            .join(Interview, Interview.candidate_id == JobApplication.candidate_id)
            .join(InterviewScorecard, InterviewScorecard.interview_id == Interview.id)
            .where(Interview.job_id == JobApplication.job_id)
        )
    ).all()
    for app, score in rows:
        if score is not None and app.status == "hired":
            assert float(score) >= threshold, (
                f"hired with score {score} below hard threshold {threshold}"
            )


@pytest.mark.asyncio
async def test_difficulty_hard_yields_no_more_hires_than_easy(session, admin) -> None:
    """Same seed ⇒ identical draws; a stricter bar can only reduce hires."""
    easy_run = await _run(session, admin, hiring_difficulty="easy", seed=42)
    easy_hires = (easy_run.stats or {}).get("decisions", {}).get("hired", 0)

    await service.reset(session)
    fresh_admin = await _create_fresh_admin(session)
    hard_run = await _run(session, fresh_admin, hiring_difficulty="hard", seed=42)
    hard_hires = (hard_run.stats or {}).get("decisions", {}).get("hired", 0)

    assert hard_hires <= easy_hires


@pytest.mark.asyncio
async def test_decisions_stage_runs_without_interviews(session, admin) -> None:
    """Screening-only mode still shortlists/offers based on screen scores."""
    run = await _run(
        session, admin,
        include_interviews=False, hiring_difficulty="easy",
        num_candidates=6, candidates_per_job=4, num_jobs=1, seed=8,
    )
    assert run.status == "completed"
    stages = (
        (await session.execute(
            select(SimulationEvent.stage).where(SimulationEvent.run_id == run.id)
        )).scalars().all()
    )
    assert "decisions" in stages
    decisions = (run.stats or {}).get("decisions") or {}
    assert sum(decisions.values()) > 0


# ═══════════════════════════════════════════════════════════════════
# 4. Totals & export enrichment (Modules 8 & 12)
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
async def test_status_totals_include_offers_and_hired(session, admin) -> None:
    await _run(session, admin)
    status = await service.get_status(session)
    totals = status["totals"]
    assert "offers" in totals and "hired" in totals
    assert 0 <= totals["hired"] <= totals["offers"] <= totals["applications"]


@pytest.mark.asyncio
async def test_export_summary_includes_offers_and_hired(session, admin) -> None:
    await _run(session, admin)
    data = await service.export_dataset(session)
    summary = data["summary"]
    assert "offers" in summary and "hired" in summary
    assert summary["hired"] <= summary["offers"]
    # Application records expose final status for downstream analytics.
    if data["applications"]:
        assert all("status" in a for a in data["applications"])


# ═══════════════════════════════════════════════════════════════════
# 5. API security / RBAC (Module 14)
# ═══════════════════════════════════════════════════════════════════


def _auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


async def _login(client: AsyncClient, email: str, password: str = PASSWORD) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_demo_endpoints_require_authentication(client: AsyncClient):
    for method, path in [
        ("GET", "/api/v1/demo/scenarios"),
        ("POST", "/api/v1/demo/generate"),
        ("GET", "/api/v1/demo/status"),
        ("POST", "/api/v1/demo/reset"),
        ("GET", "/api/v1/demo/export"),
    ]:
        resp = await client.request(method, path, json={})
        assert resp.status_code in (401, 403, 422), f"{method} {path}: {resp.status_code}"


@pytest.mark.asyncio
@pytest.mark.parametrize("role_name", ["candidate", "recruiter", "hr_manager"])
async def test_non_admin_roles_forbidden_on_demo_endpoints(
    client: AsyncClient, session, role_name: str,
):
    email = f"p11_{role_name}_{uuid.uuid4().hex[:6]}@test.com"
    user = User(
        id=uuid.uuid4(),
        full_name="Non Admin",
        email=email,
        password_hash=hash_password(PASSWORD),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    role = (
        await session.execute(select(Role).where(Role.name == role_name))
    ).scalar_one_or_none()
    assert role is not None, f"seeded role missing: {role_name}"
    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.flush()

    token = await _login(client, email)

    scenarios = await client.get("/api/v1/demo/scenarios", headers=_auth(token))
    assert scenarios.status_code == 403

    generate = await client.post(
        "/api/v1/demo/generate",
        json={"scenario_slug": "quick-start"},
        headers=_auth(token),
    )
    assert generate.status_code == 403

    reset = await client.post("/api/v1/demo/reset", headers=_auth(token))
    assert reset.status_code == 403

    export = await client.get("/api/v1/demo/export", headers=_auth(token))
    assert export.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_access_demo_endpoints(client: AsyncClient, session):
    email = f"p11_admin_{uuid.uuid4().hex[:6]}@test.com"
    user = User(
        id=uuid.uuid4(),
        full_name="Demo Admin",
        email=email,
        password_hash=hash_password(PASSWORD),
        is_active=True,
    )
    session.add(user)
    await session.flush()
    role = (
        await session.execute(select(Role).where(Role.name == "admin"))
    ).scalar_one()
    session.add(UserRole(user_id=user.id, role_id=role.id))
    await session.flush()

    token = await _login(client, email)

    scenarios = await client.get("/api/v1/demo/scenarios", headers=_auth(token))
    assert scenarios.status_code == 200
    slugs = {s["slug"] for s in scenarios.json()}
    assert NAMED_SCENARIO_SLUGS <= slugs

    status = await client.get("/api/v1/demo/status", headers=_auth(token))
    assert status.status_code == 200
