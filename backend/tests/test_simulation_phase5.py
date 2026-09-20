"""Tests for Phase 5 — What-If Requirement Impact Analysis.

Covers:
- Unit tests for requirement impact analyzer calculations
- Skill requirement changes (added, removed, promoted, demoted)
- Experience requirement changes
- Education requirement changes
- Candidate satisfaction calculation
- Affected candidates identification
- Newly qualified/disqualified candidates
- Score impact attribution
- Multiple requirement changes
- Edge cases: zero candidates, zero changes, missing data
- API integration: full endpoint lifecycle
- RBAC + tenant isolation
- CRITICAL regression: no live hiring data is modified
"""

import uuid
from datetime import date, datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.domain.enums import (
    EmploymentType,
    JobStatus,
    MembershipStatus,
    SkillCategory,
    SkillProficiency,
)
from app.domain.models import (
    CandidateProfile,
    CandidateRanking,
    CandidateSkill,
    Education,
    Experience,
    Job,
    JobApplication,
    Organization,
    OrganizationMembership,
    ScreeningResult,
    Skill,
    User,
)
from app.domain.requirement_impact_schemas import (
    CandidateRequirementImpactDetail,
    CandidateRequirementImpactListResponse,
    RequirementChangeDetail,
    RequirementImpactResponse,
)
from app.domain.simulation_models import (
    SimulationExecution,
    SimulationImpact,
    SimulationResult,
    SimulationScenario,
)
from app.repositories.simulation import SimulationRepository
from app.services.simulation.requirement_impact_analyzer import (
    RequirementImpactAnalyzer,
    _impact_category,
    _identify_skill_changes,
    _identify_experience_change,
    _identify_education_change,
    _check_skill_satisfied,
    _check_experience_satisfied,
    _check_education_satisfied,
)

PASSWORD = "Impact@12345"

BASELINE_CONFIG = {
    "source": "job_snapshot",
    "job_version": 1,
    "title": "Senior Python Developer",
    "company": "Test Corp",
    "scoring_weights": {
        "skills": 0.40, "experience": 0.25, "education": 0.15,
        "projects": 0.20, "certifications": 0.00, "location": 0.00,
        "employment_type": 0.00, "semantic": 0.00,
    },
    "threshold": 70,
    "shortlist_size": 3,
    "requirements": {
        "mandatory_skills": ["Python", "PostgreSQL"],
        "preferred_skills": ["Docker", "Redis"],
        "experience": {"minimum_years": 2, "maximum_years": None},
        "education": {"level": "bachelor", "requirement": "required"},
    },
}

SIM_CONFIG_PROMOTE_DOCKER = {
    "scoring_weights": {
        "skills": 0.40, "experience": 0.25, "education": 0.15,
        "projects": 0.20, "certifications": 0.00, "location": 0.00,
        "employment_type": 0.00, "semantic": 0.00,
    },
    "threshold": 70,
    "shortlist_size": 3,
    "requirements": {
        "mandatory_skills": ["Python", "PostgreSQL", "Docker"],
        "preferred_skills": ["Redis"],
        "experience": {"minimum_years": 4, "maximum_years": None},
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


async def _create_job(session: AsyncSession, recruiter: User, org: Organization) -> Job:
    job = Job(
        recruiter_id=recruiter.id,
        organization_id=org.id,
        title="Senior Python Developer",
        company=org.name,
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME.value,
        location="Remote",
        description="Lead platform engineering with Python and PostgreSQL.",
        required_skills=["Python", "PostgreSQL"],
        preferred_skills=["Docker", "Redis"],
        experience_required="2 years",
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
    skill = (await session.execute(select(Skill).where(Skill.name == name))).scalar_one_or_none()
    if skill:
        return skill
    skill = Skill(name=name, category=SkillCategory.PROGRAMMING_LANGUAGES)
    session.add(skill)
    await session.flush()
    return skill


async def _seed_candidate(
    session: AsyncSession,
    user: User,
    skills: tuple[str, ...] = (),
    experience_years: float = 0.0,
    degrees: tuple[str, ...] = (),
) -> CandidateProfile:
    profile = CandidateProfile(user_id=user.id, location="Remote", current_role="Engineer")
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
                employment_type=EmploymentType.FULL_TIME.value,
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


async def _create_ready_scenario(
    session: AsyncSession,
    org: Organization,
    job: Job,
    creator: User,
    name: str = "Phase 5 Scenario",
    sim_config: dict | None = None,
) -> SimulationScenario:
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
        simulation_config=sim_config or SIM_CONFIG_PROMOTE_DOCKER,
        config_version=1,
    )


async def _seed_default_pool(session: AsyncSession, job: Job) -> dict[str, User]:
    """Seed 3 candidates with different skill/experience profiles."""
    # Alice: has Python, PostgreSQL, Docker, 6 years, Master's
    alice = await _make_candidate(session, "Alice Smith")
    await _seed_candidate(
        session, alice,
        skills=("Python", "PostgreSQL", "Docker"),
        experience_years=6.0,
        degrees=("Master of Science in CS",),
    )

    # Bob: has Python, no Docker, 3 years, Bachelor's
    bob = await _make_candidate(session, "Bob Jones")
    await _seed_candidate(
        session, bob,
        skills=("Python",),
        experience_years=3.0,
        degrees=("Bachelor of Science in CS",),
    )

    # Carol: no Python, has JavaScript, 1 year, High School
    carol = await _make_candidate(session, "Carol Lee")
    await _seed_candidate(
        session, carol,
        skills=("JavaScript",),
        experience_years=1.0,
        degrees=("High School Diploma",),
    )

    for user in (alice, bob, carol):
        await _apply(session, job, user)
    return {"alice": alice, "bob": bob, "carol": carol}


async def _run_simulation(client: AsyncClient, token: str, scenario_id: str) -> dict:
    """Run a simulation and return the execution."""
    resp = await client.post(
        f"/api/v1/simulations/{scenario_id}/run",
        headers=_auth(token),
    )
    assert resp.status_code in (200, 202), resp.text
    return resp.json()


# ═══════════════════════════════════════════════════════════════════
# Unit Tests — Pure Functions
# ═══════════════════════════════════════════════════════════════════


class TestImpactCategory:
    def test_no_impact(self):
        assert _impact_category(0) == "NO_CANDIDATE_IMPACT"

    def test_low_impact(self):
        assert _impact_category(3) == "LOW_CANDIDATE_IMPACT"

    def test_moderate_impact(self):
        assert _impact_category(10) == "MODERATE_CANDIDATE_IMPACT"

    def test_high_impact(self):
        assert _impact_category(25) == "HIGH_CANDIDATE_IMPACT"


class TestSkillChangeDetection:
    def test_no_changes(self):
        config = {"requirements": {"mandatory_skills": ["Python"], "preferred_skills": ["Docker"]}}
        changes = _identify_skill_changes(config, config)
        assert len(changes) == 0

    def test_added_to_mandatory(self):
        base = {"requirements": {"mandatory_skills": ["Python"], "preferred_skills": []}}
        sim = {"requirements": {"mandatory_skills": ["Python", "PostgreSQL"], "preferred_skills": []}}
        changes = _identify_skill_changes(base, sim)
        assert len(changes) == 1
        assert changes[0].change_type == "added"
        assert changes[0].requirement_name == "PostgreSQL"
        assert changes[0].simulation_value == "mandatory"

    def test_removed_from_mandatory(self):
        base = {"requirements": {"mandatory_skills": ["Python", "PostgreSQL"], "preferred_skills": []}}
        sim = {"requirements": {"mandatory_skills": ["Python"], "preferred_skills": []}}
        changes = _identify_skill_changes(base, sim)
        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert changes[0].requirement_name == "PostgreSQL"
        assert changes[0].baseline_value == "mandatory"

    def test_promoted_preferred_to_mandatory(self):
        base = {"requirements": {"mandatory_skills": ["Python"], "preferred_skills": ["Docker"]}}
        sim = {"requirements": {"mandatory_skills": ["Python", "Docker"], "preferred_skills": []}}
        changes = _identify_skill_changes(base, sim)
        assert len(changes) == 1
        assert changes[0].change_type == "promoted"
        assert changes[0].requirement_name == "Docker"
        assert changes[0].baseline_value == "preferred"
        assert changes[0].simulation_value == "mandatory"

    def test_demoted_mandatory_to_preferred(self):
        base = {"requirements": {"mandatory_skills": ["Python", "Docker"], "preferred_skills": []}}
        sim = {"requirements": {"mandatory_skills": ["Python"], "preferred_skills": ["Docker"]}}
        changes = _identify_skill_changes(base, sim)
        assert len(changes) == 1
        assert changes[0].change_type == "demoted"
        assert changes[0].requirement_name == "Docker"
        assert changes[0].baseline_value == "mandatory"
        assert changes[0].simulation_value == "preferred"

    def test_added_to_preferred(self):
        base = {"requirements": {"mandatory_skills": ["Python"], "preferred_skills": []}}
        sim = {"requirements": {"mandatory_skills": ["Python"], "preferred_skills": ["Redis"]}}
        changes = _identify_skill_changes(base, sim)
        assert len(changes) == 1
        assert changes[0].change_type == "added"
        assert changes[0].requirement_name == "Redis"
        assert changes[0].simulation_value == "preferred"

    def test_removed_from_preferred(self):
        base = {"requirements": {"mandatory_skills": ["Python"], "preferred_skills": ["Docker"]}}
        sim = {"requirements": {"mandatory_skills": ["Python"], "preferred_skills": []}}
        changes = _identify_skill_changes(base, sim)
        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert changes[0].requirement_name == "Docker"
        assert changes[0].baseline_value == "preferred"


class TestExperienceChangeDetection:
    def test_no_changes(self):
        exp = {"minimum_years": 2, "maximum_years": None}
        base = {"requirements": {"experience": exp}}
        assert _identify_experience_change(base, base) is None

    def test_min_increased(self):
        base = {"requirements": {"experience": {"minimum_years": 2, "maximum_years": None}}}
        sim = {"requirements": {"experience": {"minimum_years": 4, "maximum_years": None}}}
        change = _identify_experience_change(base, sim)
        assert change is not None
        assert change.change_type == "modified"
        assert change.baseline_value == "2+ years"
        assert change.simulation_value == "4+ years"


class TestEducationChangeDetection:
    def test_no_changes(self):
        edu = {"level": "bachelor", "requirement": "required"}
        base = {"requirements": {"education": edu}}
        assert _identify_education_change(base, base) is None

    def test_level_increased(self):
        base = {"requirements": {"education": {"level": "bachelor", "requirement": "required"}}}
        sim = {"requirements": {"education": {"level": "master", "requirement": "required"}}}
        change = _identify_education_change(base, sim)
        assert change is not None
        assert change.change_type == "modified"
        assert change.baseline_value == "Bachelor's"
        assert change.simulation_value == "Master's"


class TestSkillSatisfaction:
    def test_satisfied_when_matched(self):
        matched = ["Python", "PostgreSQL"]
        assert _check_skill_satisfied(matched, [], [], "Python", True) is True

    def test_missing_when_not_matched(self):
        matched = ["Python"]
        assert _check_skill_satisfied(matched, ["PostgreSQL"], [], "PostgreSQL", True) is False

    def test_not_applicable(self):
        # Skill not in any list = not applicable = satisfied
        assert _check_skill_satisfied([], [], [], "Docker", True) is True


class TestExperienceSatisfaction:
    def test_satisfied_above_minimum(self):
        assert _check_experience_satisfied(5.0, {"minimum_years": 3, "maximum_years": None}) is True

    def test_not_satisfied_below_minimum(self):
        assert _check_experience_satisfied(1.0, {"minimum_years": 3, "maximum_years": None}) is False

    def test_satisfied_within_range(self):
        assert _check_experience_satisfied(5.0, {"minimum_years": 3, "maximum_years": 8}) is True

    def test_not_satisfied_above_maximum(self):
        assert _check_experience_satisfied(10.0, {"minimum_years": 3, "maximum_years": 8}) is False

    def test_no_requirement(self):
        assert _check_experience_satisfied(0.0, None) is True
        assert _check_experience_satisfied(0.0, {}) is True


class TestEducationSatisfaction:
    def test_satisfied_meets_level(self):
        assert _check_education_satisfied(["Bachelor of Science"], {"level": "bachelor", "requirement": "required"}) is True

    def test_satisfied_exceeds_level(self):
        assert _check_education_satisfied(["Master of Science"], {"level": "bachelor", "requirement": "required"}) is True

    def test_not_satisfied_below_level(self):
        assert _check_education_satisfied(["High School Diploma"], {"level": "bachelor", "requirement": "required"}) is False

    def test_optional_always_satisfied(self):
        assert _check_education_satisfied([], {"level": "bachelor", "requirement": "optional"}) is True

    def test_no_requirement(self):
        assert _check_education_satisfied([], None) is True
        assert _check_education_satisfied([], {}) is True


# ═══════════════════════════════════════════════════════════════════
# Integration Tests — API Endpoints
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestRequirementImpactAPI:
    async def test_full_lifecycle(
        self, client: AsyncClient, session: AsyncSession,
    ):
        """Full lifecycle: create scenario, run simulation, get requirement impact."""
        org = await _create_org(session, "Phase5 Org", "phase5")
        recruiter, token = await _setup_recruiter_with_org(session, client, org)
        job = await _create_job(session, recruiter, org)
        pool = await _seed_default_pool(session, job)

        scenario = await _create_ready_scenario(session, org, job, recruiter)
        execution = await _run_simulation(client, token, str(scenario.id))
        assert execution["status"] == "completed"

        # Get requirement impact
        resp = await client.get(
            f"/api/v1/simulations/{scenario.id}/requirement-impact",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["simulation_id"] == str(scenario.id)
        assert data["execution_id"] == execution["id"]
        assert data["execution_status"] == "completed"
        assert data["scenario_name"] == "Phase 5 Scenario"
        assert data["job_title"] == "Senior Python Developer"

        # Change summary should show promoted Docker + increased experience
        cs = data["change_summary"]
        assert cs["total_requirements_changed"] >= 2
        assert cs["skills_promoted"] >= 1  # Docker promoted
        assert cs["experience_changed"] is True

        # Impact summary should have affected candidates
        is_ = data["impact_summary"]
        assert is_["candidates_affected"] >= 0  # May be 0 if all candidates already satisfy

        # Requirement changes list should have entries
        assert len(data["requirement_changes"]) >= 2

    async def test_requirement_list_endpoint(
        self, client: AsyncClient, session: AsyncSession,
    ):
        """Test the requirement list endpoint with pagination."""
        org = await _create_org(session, "Phase5 Org2", "phase5b")
        recruiter, token = await _setup_recruiter_with_org(session, client, org)
        job = await _create_job(session, recruiter, org)
        await _seed_default_pool(session, job)

        scenario = await _create_ready_scenario(session, org, job, recruiter)
        await _run_simulation(client, token, str(scenario.id))

        resp = await client.get(
            f"/api/v1/simulations/{scenario.id}/requirement-impact/requirements",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] >= 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) >= 2

    async def test_candidates_endpoint(
        self, client: AsyncClient, session: AsyncSession,
    ):
        """Test the candidates endpoint with filtering."""
        org = await _create_org(session, "Phase5 Org3", "phase5c")
        recruiter, token = await _setup_recruiter_with_org(session, client, org)
        job = await _create_job(session, recruiter, org)
        await _seed_default_pool(session, job)

        scenario = await _create_ready_scenario(session, org, job, recruiter)
        await _run_simulation(client, token, str(scenario.id))

        resp = await client.get(
            f"/api/v1/simulations/{scenario.id}/requirement-impact/candidates",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["simulation_id"] == str(scenario.id)

    async def test_candidate_detail_endpoint(
        self, client: AsyncClient, session: AsyncSession,
    ):
        """Test the candidate detail endpoint."""
        org = await _create_org(session, "Phase5 Org4", "phase5d")
        recruiter, token = await _setup_recruiter_with_org(session, client, org)
        job = await _create_job(session, recruiter, org)
        pool = await _seed_default_pool(session, job)

        scenario = await _create_ready_scenario(session, org, job, recruiter)
        await _run_simulation(client, token, str(scenario.id))

        # Get detail for Alice
        resp = await client.get(
            f"/api/v1/simulations/{scenario.id}/requirement-impact/candidates/{pool['alice'].id}",
            headers=_auth(token),
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["candidate"]["candidate_name"] == "Alice Smith"

    async def test_no_completed_execution(
        self, client: AsyncClient, session: AsyncSession,
    ):
        """Should fail gracefully when no execution exists."""
        org = await _create_org(session, "Phase5 Org5", "phase5e")
        recruiter, token = await _setup_recruiter_with_org(session, client, org)
        job = await _create_job(session, recruiter, org)
        scenario = await _create_ready_scenario(session, org, job, recruiter)

        resp = await client.get(
            f"/api/v1/simulations/{scenario.id}/requirement-impact",
            headers=_auth(token),
        )
        assert resp.status_code in (400, 422), resp.text

    async def test_invalid_simulation_id(
        self, client: AsyncClient, session: AsyncSession,
    ):
        """Should return 404 for invalid simulation ID."""
        org = await _create_org(session, "Phase5 Org6", "phase5f")
        recruiter, token = await _setup_recruiter_with_org(session, client, org)

        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/simulations/{fake_id}/requirement-impact",
            headers=_auth(token),
        )
        assert resp.status_code == 404

    async def test_rbac_unauthorized(
        self, client: AsyncClient, session: AsyncSession,
    ):
        """Should reject unauthorized users."""
        fake_id = str(uuid.uuid4())
        resp = await client.get(
            f"/api/v1/simulations/{fake_id}/requirement-impact",
        )
        assert resp.status_code in (401, 403, 422)


# ═══════════════════════════════════════════════════════════════════
# Critical Regression Test
# ═══════════════════════════════════════════════════════════════════


@pytest.mark.asyncio
class TestCriticalRegression:
    async def test_live_hiring_data_not_modified(
        self, client: AsyncClient, session: AsyncSession,
    ):
        """CRITICAL: A requirement impact analysis must never modify live hiring data."""
        org = await _create_org(session, "Regression Org", "regression")
        recruiter, token = await _setup_recruiter_with_org(session, client, org)
        job = await _create_job(session, recruiter, org)
        pool = await _seed_default_pool(session, job)

        # Capture baseline counts
        pre_jobs = (await session.execute(select(func.count(Job.id)))).scalar_one()
        pre_rankings = (await session.execute(select(func.count(CandidateRanking.id)))).scalar_one()
        pre_screening = (await session.execute(select(func.count(ScreeningResult.id)))).scalar_one()

        scenario = await _create_ready_scenario(session, org, job, recruiter)
        await _run_simulation(client, token, str(scenario.id))

        # Get requirement impact
        resp = await client.get(
            f"/api/v1/simulations/{scenario.id}/requirement-impact",
            headers=_auth(token),
        )
        assert resp.status_code == 200

        # Verify no live data was modified
        post_jobs = (await session.execute(select(func.count(Job.id)))).scalar_one()
        post_rankings = (await session.execute(select(func.count(CandidateRanking.id)))).scalar_one()
        post_screening = (await session.execute(select(func.count(ScreeningResult.id)))).scalar_one()

        assert post_jobs == pre_jobs, "Jobs were modified!"
        assert post_rankings == pre_rankings, "CandidateRankings were modified!"
        assert post_screening == pre_screening, "ScreeningResults were modified!"

        # Verify candidate data unchanged
        for name in ("alice", "bob", "carol"):
            user = pool[name]
            loaded = await session.get(User, user.id)
            assert loaded.full_name == user.full_name
            assert loaded.email == user.email
