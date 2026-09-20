"""Tests for the AI Demo Data Generator & Recruitment Simulation Platform."""

from __future__ import annotations

import random

import pytest
import pytest_asyncio
from sqlalchemy import func, select

from app.domain.agent_models import KnowledgeDocument
from app.domain.analytics_models import AnalyticsReport
from app.domain.demo_models import DemoCompany, DemoRun, DemoScenario, SimulationEvent
from app.domain.demo_schemas import DemoGenerateRequest
from app.domain.models import (
    CandidateProfile,
    Interview,
    InterviewScorecard,
    Job,
    JobApplication,
    Resume,
    ScreeningResult,
    User,
    UserRole,
)
from app.services.demo.demo_service import DEMO_EMAIL_DOMAIN, DemoService
from app.services.demo.pipeline_simulator import PipelineSimulator

service = DemoService()


async def _count(session, model) -> int:
    return (await session.execute(select(func.count()).select_from(model))).scalar() or 0


async def _demo_user_count(session) -> int:
    return (await session.execute(
        select(func.count()).select_from(User).where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))
    )).scalar() or 0


async def _create_admin(session) -> User:
    simulator = PipelineSimulator(session)
    return await simulator.create_user(
        random.Random(0), "admin", "admin@hirecraft.ai",
    )


async def _run_small_generation(session, admin: User) -> DemoRun:
    request = DemoGenerateRequest(
        num_candidates=3,
        num_recruiters=1,
        num_hr=1,
        num_jobs=1,
        candidates_per_job=2,
        include_screening=True,
        include_interviews=True,
        include_reports=True,
        include_agent_indexing=True,
        resume_format="txt",
        seed=7,
    )
    run = await service.create_run(session, request, admin.id)
    await service.generate_run(run, session, commit_stages=False)
    await session.flush()
    return run


@pytest_asyncio.fixture
async def admin(session) -> User:
    return await _create_admin(session)


async def test_list_scenarios(session) -> None:
    scenarios = await service.list_scenarios(session)
    assert len(scenarios) == 13
    slugs = {s.slug for s in scenarios}
    assert {"quick-start", "full-pipeline", "screening-only", "talent-pool"} <= slugs
    quick = next(s for s in scenarios if s.slug == "quick-start")
    assert quick.config["num_candidates"] == 10


async def test_ensure_scenarios_idempotent(session) -> None:
    first = await service.ensure_scenarios(session)
    second = await service.ensure_scenarios(session)
    assert len(first) == 13
    assert len(second) == 13
    assert (await _count(session, DemoScenario)) == 13


async def test_generate_pipeline(session, admin) -> None:
    run = await _run_small_generation(session, admin)

    assert run.status == "completed"
    assert run.progress == 100
    assert run.current_stage == "completed"
    assert run.error is None
    stats = run.stats or {}
    assert stats["companies"]
    assert stats["users"]
    assert stats["jobs"]
    assert stats["resumes"]

    assert await _demo_user_count(session) == 5  # 3 candidates + 1 recruiter + 1 hr
    assert await _count(session, Job) == 1
    assert await _count(session, Resume) == 3
    assert await _count(session, CandidateProfile) == 3
    assert await _count(session, JobApplication) == 2
    assert await _count(session, ScreeningResult) == 2
    assert await _count(session, Interview) == 2
    assert await _count(session, InterviewScorecard) == 2
    assert await _count(session, AnalyticsReport) == 3
    assert await _count(session, KnowledgeDocument) == 5  # 1 job + 1 company + 3 candidates
    assert await _count(session, DemoCompany) == 1

    assert stats["applications"] == 2
    assert stats["screenings"] == 2
    assert stats["interviews"] == 2
    assert stats["scorecards"] == 2
    assert stats["reports"] == 3
    assert stats["agent_documents"] == 5


async def test_progress_is_cumulative(session, admin) -> None:
    request = DemoGenerateRequest(
        num_candidates=2, num_recruiters=1, num_hr=0, num_jobs=1,
        candidates_per_job=1, include_screening=False, include_interviews=False,
        include_reports=False, include_agent_indexing=False, resume_format="txt", seed=1,
    )
    run = await service.create_run(session, request, admin.id)
    await service.generate_run(run, session, commit_stages=False)
    await session.flush()

    assert run.progress == 100
    events = (await session.execute(
        select(SimulationEvent).where(SimulationEvent.run_id == run.id)
        .order_by(SimulationEvent.created_at)
    )).scalars().all()
    stages = [e.stage for e in events]
    assert stages[0] == "start"
    assert stages[-1] == "completed"
    # Screening/interviews/reports/agent indexing were disabled, so the
    # progress stages in between still run in dependency order.
    assert "candidates" in stages
    assert "jobs" in stages
    assert "applications" in stages
    assert "screening" not in stages
    assert "interviews" not in stages


async def test_get_status_and_totals(session, admin) -> None:
    run = await _run_small_generation(session, admin)
    status = await service.get_status(session)
    assert status["latest_run"] is not None
    assert status["latest_run"].id == run.id
    assert len(status["runs"]) == 1
    totals = status["totals"]
    assert totals["users"] == 5
    assert totals["candidates"] == 3
    assert totals["jobs"] == 1
    assert totals["resumes"] == 3
    assert totals["applications"] == 2
    assert totals["screenings"] == 2
    assert totals["interviews"] == 2
    assert totals["reports"] == 3
    assert totals["companies"] == 1


async def test_get_run_detail(session, admin) -> None:
    run = await _run_small_generation(session, admin)
    detail = await service.get_run_detail(session, run.id)
    assert detail is not None
    assert detail["run"].status == "completed"
    assert detail["events"]


async def test_reset_clears_demo_data(session, admin) -> None:
    run = await _run_small_generation(session, admin)
    run_id = run.id

    counts = await service.reset(session)
    assert counts["users_deleted"] == 5
    assert counts["jobs_deleted"] == 1
    assert counts["resumes_deleted"] == 3
    assert counts["interviews_deleted"] == 2
    assert counts["screenings_deleted"] == 2

    assert await _demo_user_count(session) == 0
    assert await _count(session, Job) == 0
    assert await _count(session, Resume) == 0
    assert await _count(session, CandidateProfile) == 0
    assert await _count(session, JobApplication) == 0
    assert await _count(session, ScreeningResult) == 0
    assert await _count(session, Interview) == 0
    assert await _count(session, AnalyticsReport) == 0
    assert await _count(session, DemoCompany) == 0
    assert await _count(session, DemoRun) == 0
    assert await _count(session, SimulationEvent) == 0
    assert await session.get(DemoRun, run_id) is None

    second = await service.reset(session)
    assert second["users_deleted"] == 0
    assert second["jobs_deleted"] == 0


async def test_export_dataset(session, admin) -> None:
    run = await _run_small_generation(session, admin)
    data = await service.export_dataset(session)
    assert data["summary"]["users"] == 5
    assert data["summary"]["jobs"] == 1
    assert data["summary"]["applications"] == 2
    assert data["summary"]["screenings"] == 2
    assert data["summary"]["interviews"] == 2
    assert data["summary"]["reports"] == 3
    assert data["companies"]
    assert all(u["email"].endswith(f"@{DEMO_EMAIL_DOMAIN}") for u in data["users"])
    assert all(j["id"] for j in data["jobs"])


async def test_custom_companies_and_titles(session, admin) -> None:
    from app.domain.demo_schemas import DemoCustomRequest

    request = DemoCustomRequest(
        companies=["Acme Robotics", "Nimbus Cloud"],
        job_titles=["Senior Software Engineer", "Data Scientist"],
        num_candidates=2, num_recruiters=1, num_hr=0, num_jobs=2,
        candidates_per_job=1, include_screening=True, include_interviews=False,
        include_reports=False, include_agent_indexing=False, resume_format="txt", seed=3,
    )
    run = await service.create_run(session, request, admin.id)
    await service.generate_run(run, session, commit_stages=False)
    await session.flush()

    companies = {c.name for c in (await session.execute(select(DemoCompany))).scalars().all()}
    assert companies == {"Acme Robotics", "Nimbus Cloud"}
    titles = {j.title for j in (await session.execute(select(Job))).scalars().all()}
    assert titles == {"Senior Software Engineer", "Data Scientist"}
    assert run.status == "completed"
