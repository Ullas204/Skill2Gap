"""AI Demo Data Generator & Recruitment Simulation Platform - orchestrator."""

from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.db.session import async_session_factory
from app.domain.demo_models import DemoCompany, DemoRun, DemoScenario, SimulationEvent
from app.domain.demo_schemas import (
    DemoCustomRequest,
    DemoGenerateRequest,
    DemoRunResponse,
    DemoScenarioResponse,
)
from app.domain.agent_models import (
    AgentActivityLog,
    AgentConversation,
    AgentMessage,
    AgentToolExecution,
    AgentWorkflow,
    KnowledgeDocument,
)
from app.domain.analytics_models import (
    AlertRule,
    AnalyticsInsight,
    AnalyticsReport,
    DashboardLayout,
    ScheduledReport,
)
from app.domain.models import (
    AuditLog,
    CandidateProfile,
    CandidateRanking,
    CandidateSkill,
    Certification,
    CodingAssessment,
    Education,
    Experience,
    Interview,
    InterviewAnswer,
    InterviewEvaluation,
    InterviewQuestion,
    InterviewScorecard,
    Job,
    JobApplication,
    Language,
    Notification,
    ParsedResumeData,
    Project,
    RecruiterNote,
    RefreshToken,
    Resume,
    ResumeAnalysis,
    Role,
    SavedJob,
    ScreeningResult,
    SkillGapAnalysis,
    User,
    UserRole,
)
from app.services.audit import log_audit_event
from app.services.demo import data_pool
from app.services.demo.pipeline_simulator import PipelineSimulator

logger = get_logger(__name__)

DEMO_EMAIL_DOMAIN = "hirecraft.demo"

RESUME_FORMATS = ["pdf", "docx", "txt"]

STAGE_ORDER = [
    "start",
    "companies",
    "recruiters",
    "hr",
    "candidates",
    "jobs",
    "applications",
    "screening",
    "interviews",
    "decisions",
    "reports",
    "agent_indexing",
]

STAGE_WEIGHTS = {
    "companies": 5,
    "recruiters": 5,
    "hr": 3,
    "candidates": 33,
    "jobs": 9,
    "applications": 7,
    "screening": 11,
    "interviews": 13,
    "decisions": 6,
    "reports": 4,
    "agent_indexing": 3,
}

# Phase 11, Module 9: named recruitment scenarios. `industry_key` selects the
# company/title pools from data_pool; `skill_categories` narrows the skills.
SCENARIOS: list[dict] = [
    {
        "name": "Quick Start",
        "slug": "quick-start",
        "description": "A small dataset to explore the platform quickly.",
        "tags": ["small", "screening", "interviews"],
        "config": {
            "num_candidates": 10,
            "num_recruiters": 2,
            "num_hr": 1,
            "num_jobs": 3,
            "candidates_per_job": 6,
            "include_screening": True,
            "include_interviews": True,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "mixed",
        },
    },
    {
        "name": "Full Pipeline",
        "slug": "full-pipeline",
        "description": "End-to-end hiring simulation with screening, interviews and analytics.",
        "tags": ["full", "screening", "interviews", "reports"],
        "config": {
            "num_candidates": 20,
            "num_recruiters": 3,
            "num_hr": 2,
            "num_jobs": 5,
            "candidates_per_job": 8,
            "include_screening": True,
            "include_interviews": True,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "mixed",
        },
    },
    {
        "name": "Screening Only",
        "slug": "screening-only",
        "description": "Large candidate pool with AI screening and rankings, no interviews.",
        "tags": ["screening", "large"],
        "config": {
            "num_candidates": 30,
            "num_recruiters": 3,
            "num_hr": 1,
            "num_jobs": 6,
            "candidates_per_job": 10,
            "include_screening": True,
            "include_interviews": False,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "mixed",
        },
    },
    {
        "name": "Talent Pool",
        "slug": "talent-pool",
        "description": "Build a broad candidate talent pool with resumes and profiles.",
        "tags": ["profiles", "resumes"],
        "config": {
            "num_candidates": 40,
            "num_recruiters": 2,
            "num_hr": 1,
            "num_jobs": 4,
            "candidates_per_job": 8,
            "include_screening": True,
            "include_interviews": True,
            "include_reports": False,
            "include_agent_indexing": True,
            "resume_format": "mixed",
        },
    },
    # ── Phase 11 named scenarios ────────────────────────────────────
    {
        "name": "Campus Placement",
        "slug": "campus-placement",
        "description": "Entry-level campus recruitment drive with trainee roles and mass aptitude screening.",
        "tags": ["campus", "entry-level", "volume"],
        "config": {
            "industry_key": "campus",
            "num_companies": 3,
            "num_jobs": 4,
            "job_titles": data_pool.INDUSTRY_JOB_TITLES["campus"],
            "skill_categories": ["engineering"],
            "num_candidates": 30,
            "num_recruiters": 3,
            "num_hr": 1,
            "candidates_per_job": 10,
            "hiring_difficulty": "easy",
            "include_screening": True,
            "include_interviews": True,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "pdf",
        },
    },
    {
        "name": "Startup Hiring",
        "slug": "startup-hiring",
        "description": "Lean startup hiring across product and engineering with high offer rates.",
        "tags": ["startup", "product", "engineering"],
        "config": {
            "industry_key": "startup",
            "num_companies": 2,
            "num_jobs": 4,
            "job_titles": data_pool.INDUSTRY_JOB_TITLES["startup"],
            "skill_categories": ["engineering", "data_ai"],
            "num_candidates": 16,
            "num_recruiters": 2,
            "num_hr": 1,
            "candidates_per_job": 6,
            "hiring_difficulty": "easy",
            "include_screening": True,
            "include_interviews": True,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "mixed",
        },
    },
    {
        "name": "Enterprise Hiring",
        "slug": "enterprise-hiring",
        "description": "Large-organization hiring for senior roles with strict interview bars.",
        "tags": ["enterprise", "senior", "strict"],
        "config": {
            "industry_key": "enterprise",
            "num_companies": 3,
            "num_jobs": 5,
            "job_titles": data_pool.INDUSTRY_JOB_TITLES["enterprise"],
            "skill_categories": ["engineering", "cloud_devops"],
            "num_candidates": 24,
            "num_recruiters": 4,
            "num_hr": 2,
            "candidates_per_job": 8,
            "hiring_difficulty": "hard",
            "include_screening": True,
            "include_interviews": True,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "docx",
        },
    },
    {
        "name": "IT Company Hiring",
        "slug": "it-company-hiring",
        "description": "Classic software house staffing: engineering, DevOps, QA and security.",
        "tags": ["it", "engineering", "devops"],
        "config": {
            "industry_key": "it",
            "num_companies": 2,
            "num_jobs": 5,
            "job_titles": data_pool.INDUSTRY_JOB_TITLES["it"],
            "skill_categories": ["engineering", "cloud_devops", "data_ai"],
            "num_candidates": 22,
            "num_recruiters": 3,
            "num_hr": 1,
            "candidates_per_job": 8,
            "hiring_difficulty": "medium",
            "include_screening": True,
            "include_interviews": True,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "mixed",
        },
    },
    {
        "name": "Healthcare Hiring",
        "slug": "healthcare-recruitment",
        "description": "Hospital network recruiting clinical and health-tech staff.",
        "tags": ["healthcare", "clinical", "compliance"],
        "config": {
            "industry_key": "healthcare",
            "num_companies": 2,
            "num_jobs": 4,
            "job_titles": data_pool.INDUSTRY_JOB_TITLES["healthcare"],
            "skill_categories": ["healthcare", "data_ai"],
            "num_candidates": 18,
            "num_recruiters": 2,
            "num_hr": 2,
            "candidates_per_job": 7,
            "hiring_difficulty": "medium",
            "include_screening": True,
            "include_interviews": True,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "pdf",
        },
    },
    {
        "name": "Mass Hiring",
        "slug": "mass-hiring",
        "description": "High-volume hourly workforce campaign with rapid screening.",
        "tags": ["mass", "volume", "operations"],
        "config": {
            "industry_key": "mass",
            "num_companies": 2,
            "num_jobs": 4,
            "job_titles": data_pool.INDUSTRY_JOB_TITLES["mass"],
            "skill_categories": ["support_operations"],
            "num_candidates": 40,
            "num_recruiters": 4,
            "num_hr": 2,
            "candidates_per_job": 15,
            "hiring_difficulty": "easy",
            "include_screening": True,
            "include_interviews": False,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "txt",
        },
    },
    {
        "name": "Remote Hiring",
        "slug": "remote-hiring",
        "description": "Distributed-first company building a remote team worldwide.",
        "tags": ["remote", "distributed"],
        "config": {
            "industry_key": "remote",
            "num_companies": 2,
            "num_jobs": 4,
            "job_titles": data_pool.INDUSTRY_JOB_TITLES["remote"],
            "skill_categories": ["engineering", "cloud_devops"],
            "num_candidates": 18,
            "num_recruiters": 2,
            "num_hr": 1,
            "candidates_per_job": 7,
            "hiring_difficulty": "medium",
            "include_screening": True,
            "include_interviews": True,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "pdf",
        },
    },
    {
        "name": "Finance Recruitment",
        "slug": "finance-recruitment",
        "description": "Banking and capital-markets hiring with compliance-heavy screening.",
        "tags": ["finance", "risk", "compliance"],
        "config": {
            "industry_key": "finance",
            "num_companies": 3,
            "num_jobs": 4,
            "job_titles": data_pool.INDUSTRY_JOB_TITLES["finance"],
            "skill_categories": ["finance", "data_ai"],
            "num_candidates": 20,
            "num_recruiters": 3,
            "num_hr": 1,
            "candidates_per_job": 8,
            "hiring_difficulty": "hard",
            "include_screening": True,
            "include_interviews": True,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "docx",
        },
    },
    {
        "name": "Government Recruitment",
        "slug": "government-recruitment",
        "description": "Public-sector vacancy drive with structured eligibility screening.",
        "tags": ["government", "public-sector"],
        "config": {
            "industry_key": "government",
            "num_companies": 2,
            "num_jobs": 4,
            "job_titles": data_pool.INDUSTRY_JOB_TITLES["government"],
            "skill_categories": ["government", "support_operations"],
            "num_candidates": 24,
            "num_recruiters": 2,
            "num_hr": 2,
            "candidates_per_job": 10,
            "hiring_difficulty": "medium",
            "include_screening": True,
            "include_interviews": False,
            "include_reports": True,
            "include_agent_indexing": True,
            "resume_format": "pdf",
        },
    },
]


def _to_run_response(run: DemoRun) -> DemoRunResponse:
    return DemoRunResponse(
        id=run.id,
        scenario_id=run.scenario_id,
        status=run.status,
        progress=run.progress,
        current_stage=run.current_stage,
        stage_message=run.stage_message,
        stats=run.stats,
        error=run.error,
        created_at=run.created_at,
        started_at=run.started_at,
        completed_at=run.completed_at,
    )


class DemoService:
    """Facade for the demo platform operations."""

    # ─── Scenarios ──────────────────────────────────────────────────

    async def ensure_scenarios(self, session: AsyncSession) -> list[DemoScenario]:
        """Upsert scenario presets by slug (Phase 11: new presets appear on
        existing deployments; existing rows get refreshed config)."""
        existing = {
            s.slug: s
            for s in (await session.execute(select(DemoScenario))).scalars().all()
        }
        for data in SCENARIOS:
            row = existing.get(data["slug"])
            if row:
                row.name = data["name"]
                row.description = data["description"]
                row.config = data["config"]
                row.tags = data["tags"]
            else:
                row = DemoScenario(
                    name=data["name"],
                    slug=data["slug"],
                    description=data["description"],
                    is_active=True,
                    config=data["config"],
                    tags=data["tags"],
                )
                session.add(row)
        await session.flush()
        return (
            (await session.execute(select(DemoScenario).order_by(DemoScenario.created_at)))
            .scalars()
            .all()
        )

    async def list_scenarios(self, session: AsyncSession) -> list[DemoScenarioResponse]:
        scenarios = await self.ensure_scenarios(session)
        return [
            DemoScenarioResponse(
                id=s.id,
                name=s.name,
                slug=s.slug,
                description=s.description,
                is_active=s.is_active,
                config=s.config,
                tags=s.tags,
            )
            for s in scenarios
        ]

    # ─── Runs ───────────────────────────────────────────────────────

    async def create_run(
        self,
        session: AsyncSession,
        request: DemoGenerateRequest | DemoCustomRequest,
        admin_id: uuid.UUID,
    ) -> DemoRun:
        await self.ensure_scenarios(session)
        resolved: dict = {}
        scenario: DemoScenario | None = None
        scenario_slug = getattr(request, "scenario_slug", None)
        if scenario_slug:
            scenario = (
                await session.execute(
                    select(DemoScenario).where(DemoScenario.slug == scenario_slug)
                )
            ).scalar_one_or_none()
            if scenario and scenario.config:
                resolved.update(dict(scenario.config))

        payload = request.model_dump(exclude_unset=True)
        payload.pop("scenario_slug", None)
        resolved.update(payload)

        if isinstance(request, DemoCustomRequest):
            companies_pool = data_pool.COMPANIES
            if request.companies:
                resolved["companies"] = [
                    {"name": name, "industry": "Technology", "headquarters": "Remote",
                     "size_range": "51-200"}
                    for name in request.companies
                ]
            if request.job_titles:
                resolved["job_titles"] = request.job_titles

        # Phase 11: named industry scenarios carry an `industry_key` that
        # selects the company pool at generation time.
        industry_key = (scenario.config or {}).get("industry_key") if scenario else None
        if industry_key and not resolved.get("companies"):
            resolved["industry_companies"] = data_pool.INDUSTRY_COMPANIES.get(
                industry_key, data_pool.COMPANIES,
            )
            if not resolved.get("job_titles"):
                resolved["job_titles"] = list(data_pool.INDUSTRY_JOB_TITLES.get(industry_key, data_pool.JOB_TITLES))

        run = DemoRun(
            user_id=admin_id,
            scenario_id=scenario.id if scenario else None,
            status="queued",
            progress=0,
            current_stage=None,
            stage_message="Queued",
            config=resolved,
            stats={},
        )
        session.add(run)
        await session.flush()
        return run

    async def start_generation(
        self,
        session: AsyncSession,
        request: DemoGenerateRequest | DemoCustomRequest,
        admin_id: uuid.UUID,
        background_tasks: BackgroundTasks,
    ) -> DemoRun:
        run = await self.create_run(session, request, admin_id)
        await session.commit()
        background_tasks.add_task(self.run_background, run.id)
        return run

    async def run_background(self, run_id: uuid.UUID) -> None:
        async with async_session_factory() as session:
            run = await session.get(DemoRun, run_id)
            if not run:
                return
            try:
                await self.generate_run(run, session, commit_stages=True)
            except Exception as exc:  # pragma: no cover - background error path
                logger.exception("Demo generation %s failed", run_id)
                run.status = "failed"
                run.error = str(exc)[:500]
                run.completed_at = datetime.now(timezone.utc)
                await session.commit()

    async def generate_run(
        self,
        run: DemoRun,
        session: AsyncSession,
        commit_stages: bool = False,
    ) -> DemoRun:
        simulator = PipelineSimulator(session)
        rng = random.Random((run.config or {}).get("seed") or 42)
        cfg = dict(run.config or {})

        stats: dict = {
            "companies": [],
            "users": [],
            "jobs": [],
            "resumes": [],
            "applications": 0,
            "screenings": 0,
            "interviews": 0,
            "scorecards": 0,
            "reports": 0,
            "agent_documents": 0,
        }

        run.status = "running"
        run.started_at = datetime.now(timezone.utc)
        run.error = None

        admin_user = await session.get(User, run.user_id)
        if admin_user is None:
            raise ValueError("Demo run owner not found")

        await self._progress(
            session, run, "start", "Starting demo generation", commit_stages,
        )

        # ── 1. Companies ────────────────────────────────────────────
        await self._progress(
            session, run, "companies", "Generating demo companies", commit_stages,
        )
        companies_cfg = cfg.get("companies")
        if not companies_cfg:
            pool = cfg.get("industry_companies") or data_pool.COMPANIES
            desired = cfg.get("num_companies") or min(cfg.get("num_jobs", 5), len(pool))
            picked = rng.sample(pool, k=min(desired, len(pool)))
            companies_cfg = [dict(c) for c in picked]
        company_rows = []
        for company_cfg in companies_cfg:
            company = await simulator.create_company(rng, company_cfg)
            company_rows.append(company)
            stats["companies"].append({"id": str(company.id), "name": company.name, "industry": company.industry})

        # ── 2. Recruiters ───────────────────────────────────────────
        await self._progress(
            session, run, "recruiters", "Creating demo recruiters", commit_stages,
        )
        recruiters: list[User] = []
        for i in range(cfg.get("num_recruiters", 3)):
            email = f"demo.recruiter.{rng.randint(1000, 9999)}@{DEMO_EMAIL_DOMAIN}"
            user = await simulator.create_user(rng, "recruiter", email)
            recruiters.append(user)
            stats["users"].append({"id": str(user.id), "name": user.full_name, "email": user.email, "roles": ["recruiter"]})

        # ── 3. HR users ─────────────────────────────────────────────
        await self._progress(session, run, "hr", "Creating demo HR users", commit_stages)
        hr_users: list[User] = []
        for i in range(cfg.get("num_hr", 1)):
            email = f"demo.hr.{rng.randint(1000, 9999)}@{DEMO_EMAIL_DOMAIN}"
            user = await simulator.create_user(rng, "hr", email)
            hr_users.append(user)
            stats["users"].append({"id": str(user.id), "name": user.full_name, "email": user.email, "roles": ["hr"]})

        # ── 4. Candidates + profiles + resumes ─────────────────────
        await self._progress(
            session, run, "candidates", "Creating candidates, profiles and resumes",
            commit_stages,
        )
        skill_pool = simulator.resolve_skill_pool(rng, cfg.get("skill_categories"))
        job_titles_pool = list(data_pool.JOB_TITLES)
        candidates: list[dict] = []
        num_candidates = cfg.get("num_candidates", 20)
        resume_format = cfg.get("resume_format", "mixed")
        for i in range(num_candidates):
            job_title = rng.choice(job_titles_pool)
            skill_names = rng.sample(
                skill_pool, k=min(rng.randint(5, 12), len(skill_pool)),
            )
            email = f"demo.candidate.{rng.randint(1000, 9999)}@{DEMO_EMAIL_DOMAIN}"
            user = await simulator.create_user(rng, "candidate", email)
            profile = await simulator.create_candidate_profile(
                rng, user, job_title, skill_names,
                [c["name"] for c in stats["companies"]],
            )
            fmt = resume_format if resume_format != "mixed" else rng.choice(RESUME_FORMATS)
            resume = await simulator.create_resume(
                rng, user, profile, job_title, skill_names,
                [c["name"] for c in stats["companies"]], fmt,
            )
            stats["users"].append({"id": str(user.id), "name": user.full_name, "email": user.email, "roles": ["candidate"]})
            stats["resumes"].append({"id": str(resume.id), "format": fmt})
            candidates.append({
                "user": user,
                "profile": profile,
                "resume": resume,
                "skills": skill_names,
                "job_title": job_title,
            })

        # ── 5. Jobs ─────────────────────────────────────────────────
        await self._progress(session, run, "jobs", "Publishing demo jobs", commit_stages)
        job_titles_cfg = cfg.get("job_titles") or rng.sample(
            job_titles_pool, k=min(cfg.get("num_jobs", 5), len(job_titles_pool))
        )
        jobs = []
        num_jobs = min(cfg.get("num_jobs", 5), len(job_titles_cfg))
        for i in range(num_jobs):
            recruiter = rng.choice(recruiters)
            company = company_rows[i % len(company_rows)]
            required = rng.sample(skill_pool, k=min(5, len(skill_pool)))
            preferred = rng.sample(
                [s for s in skill_pool if s not in required],
                k=min(3, max(len(skill_pool) - len(required), 0)),
            )
            job = await simulator.create_job(
                rng, recruiter, company.name, job_titles_cfg[i],
                required, preferred,
            )
            jobs.append(job)
            stats["jobs"].append({"id": str(job.id), "title": job.title, "company": job.company})

        # ── 6. Applications ─────────────────────────────────────────
        await self._progress(
            session, run, "applications", "Creating job applications", commit_stages,
        )
        candidates_per_job = cfg.get("candidates_per_job", 8)
        applications = []
        for job in jobs:
            pool = list(candidates)
            rng.shuffle(pool)
            for candidate in pool[: min(candidates_per_job, len(pool))]:
                app = await simulator.create_application(job, candidate["user"], candidate["resume"])
                applications.append({"app": app, "job": job, "candidate": candidate})
                stats["applications"] += 1

        # ── 7. Screening ────────────────────────────────────────────
        screened_jobs: list[Job] = []
        if cfg.get("include_screening", True):
            await self._progress(session, run, "screening", "Running AI screening", commit_stages)
            for job in jobs:
                count = await simulator.screen_job(job.id, job.recruiter_id)
                stats["screenings"] += count
                screened_jobs.append(job)

        # ── 8. Interviews ───────────────────────────────────────────
        hiring_difficulty = cfg.get("hiring_difficulty", "medium")
        if cfg.get("include_interviews", True):
            await self._progress(session, run, "interviews", "Simulating interviews", commit_stages)
            for job in jobs:
                job_apps = [a for a in applications if a["job"].id == job.id]
                top = job_apps[: min(3, len(job_apps))]
                for entry in top:
                    try:
                        result = await simulator.run_interview(
                            rng, job, entry["candidate"]["user"], job.recruiter_id,
                            difficulty=hiring_difficulty, count=8,
                        )
                        stats["interviews"] += 1
                        if result.get("scorecard"):
                            stats["scorecards"] += 1
                    except ValueError:
                        logger.warning("Interview simulation skipped for job %s", job.id)

        # ── 8b. Hiring decisions (Phase 11, Modules 6 & 10) ────────
        await self._progress(
            session, run, "decisions",
            f"Running shortlisting and hiring decisions ({hiring_difficulty})",
            commit_stages,
        )
        decision_totals = {
            "shortlisted": 0, "interview_scheduled": 0,
            "offered": 0, "hired": 0, "rejected": 0,
        }
        for job in jobs:
            job_entries = [a for a in applications if a["job"].id == job.id]
            if not job_entries:
                continue
            name_by_app = {
                str(e["app"].id): e["candidate"]["user"].full_name
                for e in job_entries
            }
            outcome = await simulator.run_hiring_decisions(
                rng, job, job_entries, difficulty=hiring_difficulty,
            )
            counts = outcome["counts"]
            for key in decision_totals:
                decision_totals[key] += counts[key]
            hired_names = [
                name_by_app[t["application_id"]]
                for t in outcome["transitions"] if t["to"] == "hired"
            ]
            message = (
                f"{job.title} @ {job.company}: {counts['shortlisted']} shortlisted, "
                f"{counts['offered']} offers, {counts['hired']} hired, "
                f"{counts['rejected']} rejected"
            )
            await self._event(
                session, run, "decisions", "success", message,
                details={"job_id": str(job.id), "transitions": outcome["transitions"],
                         "hired": hired_names},
            )
        stats["decisions"] = decision_totals
        try:
            await log_audit_event(
                session,
                user_id=run.user_id,
                action="demo.decisions",
                resource_type="demo_run",
                resource_id=str(run.id),
                details=decision_totals,
            )
        except Exception:
            logger.exception("Decision audit logging failed for run %s", run.id)

        # ── 9. Analytics reports ────────────────────────────────────
        if cfg.get("include_reports", True):
            await self._progress(session, run, "reports", "Generating analytics reports", commit_stages)
            for recruiter in recruiters:
                await simulator.create_report(
                    recruiter, "Recruiter Pipeline Overview", "recruiter",
                )
                stats["reports"] += 1
            for hr in hr_users:
                await simulator.create_report(hr, "HR Hiring Overview", "hr")
                stats["reports"] += 1
            await simulator.create_report(admin_user, "Executive Hiring Summary", "executive")
            stats["reports"] += 1

        # ── 10. Agent indexing ──────────────────────────────────────
        if cfg.get("include_agent_indexing", True):
            await self._progress(session, run, "agent_indexing", "Indexing demo knowledge", commit_stages)
            try:
                from app.rag.retriever import RAGRetriever

                retriever = RAGRetriever(db=session)
                for job in jobs:
                    content = f"Job: {job.title} at {job.company}. {job.description[:300]}"
                    await retriever.index_document(
                        "job", str(job.id), job.title, content,
                        {"company": job.company, "demo": True},
                    )
                    stats["agent_documents"] += 1
                for company in company_rows:
                    await retriever.index_document(
                        "company", str(company.id), company.name,
                        company.description or f"{company.name} - {company.industry}",
                        {"industry": company.industry, "demo": True},
                    )
                    stats["agent_documents"] += 1
                for cand in candidates:
                    profile = cand["profile"]
                    content = (
                        f"Candidate profile. Current role: {profile.current_role or 'N/A'}. "
                        f"Location: {profile.location or 'N/A'}. Skills: {', '.join(cand['skills'])}"
                    )
                    await retriever.index_document(
                        "candidate", str(profile.id), cand["user"].full_name, content,
                        {"demo": True},
                    )
                    stats["agent_documents"] += 1
            except Exception as exc:
                logger.warning("Agent indexing skipped: %s", exc)
                await self._event(
                    session, run, "agent_indexing", "warning",
                    f"Agent indexing skipped: {str(exc)[:200]}",
                )

        # ── Audit trail ─────────────────────────────────────────────
        try:
            await log_audit_event(
                session,
                user_id=run.user_id,
                action="demo.generate",
                resource_type="demo_run",
                resource_id=str(run.id),
                details={"stage": "completed", "stats": stats},
            )
        except Exception:
            logger.exception("Audit logging failed for demo run %s", run.id)

        run.stats = stats
        run.status = "completed"
        run.progress = 100
        run.current_stage = "completed"
        run.stage_message = "Demo dataset generated successfully"
        run.completed_at = datetime.now(timezone.utc)
        await self._event(
            session, run, "completed", "success", "Demo dataset generated successfully",
            details={"stats": stats},
        )
        await session.flush()
        if commit_stages:
            await session.commit()
        return run

    # ─── Progress helpers ───────────────────────────────────────────

    async def _progress(
        self,
        session: AsyncSession,
        run: DemoRun,
        stage: str,
        message: str,
        commit: bool,
    ) -> None:
        if stage in STAGE_ORDER:
            completed_weight = sum(
                STAGE_WEIGHTS[s] for s in STAGE_ORDER[: STAGE_ORDER.index(stage) + 1]
                if s in STAGE_WEIGHTS
            )
        else:
            completed_weight = 100
        progress = min(100, max(0, int(completed_weight)))
        run.current_stage = stage
        run.stage_message = message[:500]
        run.progress = max(run.progress, progress)
        await self._event(session, run, stage, "info", message)
        await session.flush()
        if commit:
            await session.commit()

    async def _event(
        self,
        session: AsyncSession,
        run: DemoRun,
        stage: str | None,
        event_type: str,
        message: str,
        details: dict | None = None,
    ) -> None:
        session.add(
            SimulationEvent(
                run_id=run.id,
                stage=stage,
                event_type=event_type,
                message=message[:500],
                details=details,
            )
        )

    # ─── Status ─────────────────────────────────────────────────────

    async def get_status(self, session: AsyncSession) -> dict:
        runs = (
            (await session.execute(select(DemoRun).order_by(DemoRun.created_at.desc())))
            .scalars()
            .all()
        )
        latest = runs[0] if runs else None
        totals = await self._totals(session)
        return {
            "latest_run": _to_run_response(latest) if latest else None,
            "runs": [_to_run_response(r) for r in runs],
            "totals": totals,
        }

    async def get_run_detail(self, session: AsyncSession, run_id: uuid.UUID) -> dict | None:
        run = await session.get(DemoRun, run_id)
        if not run:
            return None
        events = (
            (await session.execute(
                select(SimulationEvent).where(SimulationEvent.run_id == run_id)
                .order_by(SimulationEvent.created_at)
            ))
            .scalars()
            .all()
        )
        return {
            "run": _to_run_response(run),
            "events": [
                {
                    "id": e.id,
                    "stage": e.stage,
                    "event_type": e.event_type,
                    "message": e.message,
                    "details": e.details,
                    "created_at": e.created_at,
                }
                for e in events
            ],
        }

    async def _totals(self, session: AsyncSession) -> dict:
        companies = (await session.execute(select(DemoCompany))).scalars().all()
        user_ids = await self._demo_user_ids(session)
        if user_ids:
            jobs = (
                await session.execute(
                    select(func.count()).select_from(Job).where(Job.recruiter_id.in_(user_ids))
                )
            ).scalar() or 0
            applications = (
                await session.execute(
                    select(func.count()).select_from(JobApplication)
                    .where(JobApplication.candidate_id.in_(user_ids))
                )
            ).scalar() or 0
            screenings = (
                await session.execute(
                    select(func.count()).select_from(ScreeningResult)
                    .where(ScreeningResult.candidate_id.in_(user_ids))
                )
            ).scalar() or 0
            interviews = (
                await session.execute(
                    select(func.count()).select_from(Interview)
                    .where(Interview.candidate_id.in_(user_ids))
                )
            ).scalar() or 0
            offers = (
                await session.execute(
                    select(func.count()).select_from(JobApplication)
                    .where(
                        JobApplication.candidate_id.in_(user_ids),
                        JobApplication.status.in_(["offered", "hired"]),
                    )
                )
            ).scalar() or 0
            hired = (
                await session.execute(
                    select(func.count()).select_from(JobApplication)
                    .where(
                        JobApplication.candidate_id.in_(user_ids),
                        JobApplication.status == "hired",
                    )
                )
            ).scalar() or 0
            report_rows = (
                (await session.execute(select(AnalyticsReport))).scalars().all()
            )
            reports = sum(
                1 for r in report_rows
                if r.user_id in user_ids or (r.config or {}).get("source") == "demo"
            )
            resumes = (
                await session.execute(
                    select(func.count()).select_from(Resume)
                    .where(Resume.user_id.in_(user_ids))
                )
            ).scalar() or 0
            candidates = (
                await session.execute(
                    select(func.count()).select_from(UserRole)
                    .join(Role, UserRole.role_id == Role.id)
                    .where(Role.name == "candidate", UserRole.user_id.in_(user_ids))
                )
            ).scalar() or 0
        else:
            jobs = applications = screenings = interviews = reports = resumes = candidates = 0
            offers = hired = 0

        return {
            "companies": len(companies),
            "candidates": candidates,
            "users": len(user_ids),
            "jobs": jobs,
            "applications": applications,
            "screenings": screenings,
            "interviews": interviews,
            "offers": offers,
            "hired": hired,
            "reports": reports,
            "resumes": resumes,
        }

    # ─── Reset ──────────────────────────────────────────────────────

    async def _demo_user_ids(self, session: AsyncSession) -> list[uuid.UUID]:
        rows = (
            await session.execute(
                select(User.id).where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))
            )
        ).scalars().all()
        return [uuid.UUID(str(r)) for r in rows]

    async def reset(self, session: AsyncSession) -> dict:
        user_ids = await self._demo_user_ids(session)

        # Tracked ids stored in previous run stats.
        runs = (await session.execute(select(DemoRun))).scalars().all()
        tracked_user_ids: set[uuid.UUID] = set(user_ids)
        tracked_job_ids: set[uuid.UUID] = set()
        tracked_company_ids: set[uuid.UUID] = set()
        for run in runs:
            stats = run.stats or {}
            for u in stats.get("users", []):
                tracked_user_ids.add(uuid.UUID(str(u["id"])))
            for j in stats.get("jobs", []):
                tracked_job_ids.add(uuid.UUID(str(j["id"])))
            for c in stats.get("companies", []):
                tracked_company_ids.add(uuid.UUID(str(c["id"])))

        jobs = (
            (await session.execute(
                select(Job).where(
                    Job.recruiter_id.in_(tracked_user_ids) if tracked_user_ids
                    else Job.id.in_(tracked_job_ids)
                )
            ))
            .scalars()
            .all()
        ) if tracked_user_ids or tracked_job_ids else []
        job_ids = set(tracked_job_ids)
        job_ids.update(job.id for job in jobs)

        resumes = (
            (await session.execute(
                select(Resume).where(Resume.user_id.in_(tracked_user_ids))
            ))
            .scalars()
            .all()
        ) if tracked_user_ids else []
        resume_ids = {r.id for r in resumes}
        for r in resumes:
            storage = Path(r.storage_path)
            if storage.exists():
                try:
                    storage.unlink()
                except OSError:
                    logger.warning("Failed to remove resume file %s", storage)

        profiles = (
            (await session.execute(
                select(CandidateProfile).where(CandidateProfile.user_id.in_(tracked_user_ids))
            ))
            .scalars()
            .all()
        ) if tracked_user_ids else []
        profile_ids = {p.id for p in profiles}

        interview_ids: set[uuid.UUID] = set()
        if tracked_user_ids or job_ids:
            conditions = []
            if tracked_user_ids:
                conditions.append(Interview.candidate_id.in_(tracked_user_ids))
            if job_ids:
                conditions.append(Interview.job_id.in_(job_ids))
            interview_ids = {
                i.id for i in (
                    (await session.execute(select(Interview).where(or_(*conditions))))
                    .scalars()
                    .all()
                )
            }

        screening_ids: set[uuid.UUID] = set()
        if tracked_user_ids or job_ids:
            conditions = []
            if tracked_user_ids:
                conditions.append(ScreeningResult.candidate_id.in_(tracked_user_ids))
            if job_ids:
                conditions.append(ScreeningResult.job_id.in_(job_ids))
            screening_ids = {
                s.id for s in (
                    (await session.execute(select(ScreeningResult).where(or_(*conditions))))
                    .scalars()
                    .all()
                )
            }

        # Knowledge documents (agent index) + vector entries.
        if tracked_company_ids or tracked_user_ids or job_ids or profile_ids:
            source_ids = {str(i) for i in tracked_company_ids}
            source_ids.update(str(i) for i in tracked_user_ids)
            source_ids.update(str(i) for i in job_ids)
            source_ids.update(str(i) for i in profile_ids)
            docs = (
                (await session.execute(
                    select(KnowledgeDocument).where(KnowledgeDocument.source_id.in_(source_ids))
                ))
                .scalars()
                .all()
            )
            from app.rag.vector_store import vector_store

            for doc in docs:
                if doc.embedding_id:
                    vector_store.remove(doc.embedding_id)
                await session.delete(doc)

        # Delete in dependency (topological) order.
        if interview_ids:
            await session.execute(delete(InterviewScorecard).where(InterviewScorecard.interview_id.in_(interview_ids)))
            await session.execute(delete(CodingAssessment).where(CodingAssessment.interview_id.in_(interview_ids)))
            answers = (await session.execute(select(InterviewAnswer).join(InterviewQuestion, InterviewAnswer.question_id == InterviewQuestion.id).where(InterviewQuestion.interview_id.in_(interview_ids)))).scalars().all()
            answer_ids = [a.id for a in answers]
            if answer_ids:
                await session.execute(delete(InterviewEvaluation).where(InterviewEvaluation.answer_id.in_(answer_ids)))
                await session.execute(delete(InterviewAnswer).where(InterviewAnswer.id.in_(answer_ids)))
            await session.execute(delete(InterviewQuestion).where(InterviewQuestion.interview_id.in_(interview_ids)))
            await session.execute(delete(Interview).where(Interview.id.in_(interview_ids)))

        if screening_ids:
            await session.execute(delete(SkillGapAnalysis).where(SkillGapAnalysis.screening_result_id.in_(screening_ids)))
            await session.execute(delete(CandidateRanking).where(CandidateRanking.screening_result_id.in_(screening_ids)))
            await session.execute(delete(ScreeningResult).where(ScreeningResult.id.in_(screening_ids)))

        if job_ids:
            app_rows = (
                (await session.execute(select(JobApplication).where(JobApplication.job_id.in_(job_ids))))
                .scalars()
                .all()
            )
            app_ids = [a.id for a in app_rows]
            if app_ids:
                await session.execute(delete(RecruiterNote).where(RecruiterNote.job_application_id.in_(app_ids)))
                await session.execute(delete(JobApplication).where(JobApplication.id.in_(app_ids)))
            await session.execute(delete(SavedJob).where(SavedJob.job_id.in_(job_ids)))
            await session.execute(delete(Job).where(Job.id.in_(job_ids)))

        if resume_ids:
            await session.execute(delete(ParsedResumeData).where(ParsedResumeData.resume_id.in_(resume_ids)))
            await session.execute(delete(ResumeAnalysis).where(ResumeAnalysis.resume_id.in_(resume_ids)))
            await session.execute(delete(Resume).where(Resume.id.in_(resume_ids)))

        if profile_ids:
            await session.execute(delete(CandidateSkill).where(CandidateSkill.profile_id.in_(profile_ids)))
            await session.execute(delete(Education).where(Education.profile_id.in_(profile_ids)))
            await session.execute(delete(Experience).where(Experience.profile_id.in_(profile_ids)))
            await session.execute(delete(Project).where(Project.profile_id.in_(profile_ids)))
            await session.execute(delete(Certification).where(Certification.profile_id.in_(profile_ids)))
            await session.execute(delete(Language).where(Language.profile_id.in_(profile_ids)))
            await session.execute(delete(CandidateProfile).where(CandidateProfile.id.in_(profile_ids)))

        if tracked_user_ids:
            await session.execute(delete(Notification).where(Notification.user_id.in_(tracked_user_ids)))
            await session.execute(delete(RefreshToken).where(RefreshToken.user_id.in_(tracked_user_ids)))
            await session.execute(delete(AuditLog).where(AuditLog.user_id.in_(tracked_user_ids)))
            await session.execute(delete(AnalyticsReport).where(AnalyticsReport.user_id.in_(tracked_user_ids)))
            await session.execute(delete(DashboardLayout).where(DashboardLayout.user_id.in_(tracked_user_ids)))
            await session.execute(delete(AlertRule).where(AlertRule.user_id.in_(tracked_user_ids)))
            await session.execute(delete(ScheduledReport).where(ScheduledReport.user_id.in_(tracked_user_ids)))
            await session.execute(delete(AgentConversation).where(AgentConversation.user_id.in_(tracked_user_ids)))
            await session.execute(delete(AgentWorkflow).where(AgentWorkflow.user_id.in_(tracked_user_ids)))
            await session.execute(delete(AgentActivityLog).where(AgentActivityLog.user_id.in_(tracked_user_ids)))
            await session.execute(delete(UserRole).where(UserRole.user_id.in_(tracked_user_ids)))
            await session.execute(delete(User).where(User.id.in_(tracked_user_ids)))

        # Remove any remaining demo-generated reports (e.g. the executive
        # report created for the non-demo admin who triggered the run).
        demo_source_reports = (
            (await session.execute(select(AnalyticsReport))).scalars().all()
        )
        demo_source_report_ids = [
            r.id for r in demo_source_reports
            if (r.config or {}).get("source") == "demo"
        ]
        if demo_source_report_ids:
            await session.execute(
                delete(AnalyticsReport).where(AnalyticsReport.id.in_(demo_source_report_ids))
            )

        if tracked_company_ids:
            await session.execute(delete(DemoCompany).where(DemoCompany.id.in_(tracked_company_ids)))
        else:
            # Fallback: remove any demo companies left over.
            await session.execute(delete(DemoCompany))

        if runs:
            run_ids = [r.id for r in runs]
            await session.execute(delete(SimulationEvent).where(SimulationEvent.run_id.in_(run_ids)))
            await session.execute(delete(DemoRun).where(DemoRun.id.in_(run_ids)))

        await session.flush()
        return {
            "users_deleted": len(tracked_user_ids),
            "jobs_deleted": len(job_ids),
            "resumes_deleted": len(resume_ids),
            "profiles_deleted": len(profile_ids),
            "interviews_deleted": len(interview_ids),
            "screenings_deleted": len(screening_ids),
            "companies_deleted": len(tracked_company_ids),
            "runs_deleted": len(runs),
        }

    # ─── Export ─────────────────────────────────────────────────────

    async def export_dataset(self, session: AsyncSession) -> dict:
        user_ids = await self._demo_user_ids(session)
        id_set = set(user_ids)

        companies = (
            await session.execute(
                select(DemoCompany).order_by(DemoCompany.name)
            )
        ).scalars().all()

        users = (
            await session.execute(
                select(User)
                .where(User.email.like(f"%@{DEMO_EMAIL_DOMAIN}"))
                .options(
                    selectinload(User.roles).selectinload(UserRole.role),
                )
            )
        ).scalars().all()
        user_map = {u.id: u for u in users}

        jobs = (
            (await session.execute(select(Job))).scalars().all()
            if id_set else []
        )
        job_list = [
            {
                "id": str(j.id), "title": j.title, "company": j.company,
                "department": j.department, "location": j.location,
                "employment_type": j.employment_type, "status": j.status,
                "salary_min": j.salary_min, "salary_max": j.salary_max,
                "required_skills": j.required_skills,
                "preferred_skills": j.preferred_skills,
                "created_at": j.created_at.isoformat() if j.created_at else None,
            }
            for j in jobs if j.recruiter_id in id_set
        ]
        job_ids = {j["id"] for j in job_list}

        applications = []
        if id_set:
            app_rows = (
                await session.execute(
                    select(JobApplication).where(JobApplication.candidate_id.in_(id_set))
                )
            ).scalars().all()
            for a in app_rows:
                u = user_map.get(a.candidate_id)
                applications.append({
                    "id": str(a.id), "job_id": str(a.job_id),
                    "candidate_id": str(a.candidate_id),
                    "candidate_name": u.full_name if u else "",
                    "status": a.status,
                    "created_at": a.created_at.isoformat() if a.created_at else None,
                })

        screenings = []
        if id_set:
            scr_rows = (
                await session.execute(
                    select(ScreeningResult).where(ScreeningResult.candidate_id.in_(id_set))
                )
            ).scalars().all()
            screenings = [
                {
                    "id": str(s.id), "job_id": str(s.job_id),
                    "candidate_id": str(s.candidate_id),
                    "overall_match_score": s.overall_match_score,
                    "skill_match_score": s.skill_match_score,
                    "recommendation": s.recommendation,
                    "strength_level": s.strength_level,
                }
                for s in scr_rows
            ]

        interviews = []
        if id_set:
            iv_rows = (
                await session.execute(
                    select(Interview).where(Interview.candidate_id.in_(id_set))
                )
            ).scalars().all()
            for iv in iv_rows:
                sc = (
                    await session.execute(
                        select(InterviewScorecard).where(InterviewScorecard.interview_id == iv.id)
                    )
                ).scalar_one_or_none()
                interviews.append({
                    "id": str(iv.id), "job_id": str(iv.job_id),
                    "candidate_id": str(iv.candidate_id),
                    "interview_type": iv.interview_type, "status": iv.status,
                    "total_questions": iv.total_questions,
                    "questions_answered": iv.questions_answered,
                    "overall_score": sc.overall_score if sc else None,
                })

        reports = []
        report_rows = (
            (await session.execute(select(AnalyticsReport))).scalars().all()
        )
        report_rows = [
            r for r in report_rows
            if r.user_id in id_set or (r.config or {}).get("source") == "demo"
        ]
        reports = [
            {
                "id": str(r.id), "title": r.title, "report_type": r.report_type,
                "is_scheduled": r.is_scheduled,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in report_rows
        ]

        summary = {
            "companies": len(companies),
            "users": len(users),
            "jobs": len(job_list),
            "applications": len(applications),
            "screenings": len(screenings),
            "interviews": len(interviews),
            "offers": sum(1 for a in applications if a["status"] in ("offered", "hired")),
            "hired": sum(1 for a in applications if a["status"] == "hired"),
            "reports": len(reports),
        }
        return {
            "generated_at": datetime.now(timezone.utc),
            "companies": [
                {"id": str(c.id), "name": c.name, "industry": c.industry,
                 "headquarters": c.headquarters, "size_range": c.size_range}
                for c in companies
            ],
            "users": [
                {
                    "id": str(u.id), "full_name": u.full_name, "email": u.email,
                    "roles": [ur.role.name for ur in u.roles] if hasattr(u, "roles") else [],
                    "created_at": u.created_at.isoformat() if u.created_at else None,
                }
                for u in users
            ],
            "jobs": job_list,
            "applications": applications,
            "screenings": screenings,
            "interviews": interviews,
            "reports": reports,
            "summary": summary,
        }
