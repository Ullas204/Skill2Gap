"""Tests for Phase 4 — Ranking Impact Analysis.

Covers:
- Unit tests for ranking impact analyzer calculations
- Score change, rank change, movement classification
- Shortlist overlap, retention, turnover
- Qualification matrix
- Rank distribution, score distribution
- Rank stability, Spearman correlation
- Threshold impact
- Insight generation
- Top movers (deterministic ordering)
- Edge cases: zero candidates, zero shortlist, tied scores, missing values
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
from app.domain.ranking_impact_schemas import (
    CandidateImpactDetail,
    CandidateImpactListResponse,
    CandidateSingleImpactResponse,
    MovementCategorySummary,
    QualificationMatrix,
    RankBucket,
    RankingImpactResponse,
    ShortlistImpact,
    TopMover,
)
from app.domain.simulation_models import (
    SimulationExecution,
    SimulationImpact,
    SimulationResult,
    SimulationScenario,
)
from app.repositories.simulation import SimulationRepository
from app.services.simulation.ranking_impact_analyzer import (
    RankingImpactAnalyzer,
    _calculate_median,
    _calculate_mean,
    _safe_divide,
    _safe_percentage,
    _spearman_rank_correlation,
    SIGNIFICANT_IMPROVEMENT_THRESHOLD,
    IMPROVEMENT_THRESHOLD,
    DECLINE_THRESHOLD,
    SIGNIFICANT_DECLINE_THRESHOLD,
)

PASSWORD = "Impact@12345"

BASELINE_CONFIG = {
    "source": "job_snapshot",
    "job_version": 1,
    "title": "Senior Software Engineer",
    "company": "Test Corp",
    "scoring_weights": {
        "skills": 0.40, "experience": 0.25, "education": 0.15,
        "projects": 0.20, "certifications": 0.00, "location": 0.00,
        "employment_type": 0.00, "semantic": 0.00,
    },
    "threshold": 70,
    "shortlist_size": 3,
    "requirements": {
        "mandatory_skills": ["Python"],
        "preferred_skills": ["SQL", "Docker"],
    },
}

SIM_CONFIG = {
    "scoring_weights": {
        "skills": 0.60, "experience": 0.10, "education": 0.10,
        "projects": 0.05, "certifications": 0.05, "location": 0.05,
        "employment_type": 0.05, "semantic": 0.00,
    },
    "threshold": 55,
    "shortlist_size": 4,
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


async def _create_job(session: AsyncSession, recruiter: User, org: Organization) -> Job:
    job = Job(
        recruiter_id=recruiter.id,
        organization_id=org.id,
        title="Senior Software Engineer",
        company=org.name,
        department="Engineering",
        employment_type=EmploymentType.FULL_TIME.value,
        location="Remote",
        description="Lead platform engineering with Python.",
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


async def _create_scenario_via_api(
    client: AsyncClient, token: str, job: Job, name: str, sim_config: dict,
) -> dict:
    resp = await client.post(
        "/api/v1/simulations",
        headers=_auth(token),
        json={"job_id": str(job.id), "name": name, "simulation_config": sim_config},
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
    name: str = "Phase 4 Scenario",
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
        simulation_config=sim_config or SIM_CONFIG,
        config_version=1,
    )


async def _seed_default_pool(session: AsyncSession, job: Job) -> dict[str, User]:
    alice = await _make_candidate(session, "Alice Smith")
    await _seed_candidate(
        session, alice,
        skills=("Python", "SQL", "Docker"),
        experience_years=6.0,
        degrees=("Master of Science in CS",),
    )
    bob = await _make_candidate(session, "Bob Jones")
    await _seed_candidate(
        session, bob,
        skills=("Python",),
        experience_years=3.0,
        degrees=("Bachelor of Science in CS",),
    )
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


# ─────────────────────────────────────────────────────────────────────
# 1. Unit Tests — Pure Utility Functions
# ─────────────────────────────────────────────────────────────────────


class TestUtilityFunctions:
    def test_safe_divide_normal(self) -> None:
        assert _safe_divide(10, 2) == 5.0

    def test_safe_divide_by_zero(self) -> None:
        assert _safe_divide(10, 0) == 0.0
        assert _safe_divide(10, 0, default=-1.0) == -1.0

    def test_safe_percentage(self) -> None:
        assert _safe_percentage(25, 100) == 25.0
        assert _safe_percentage(1, 3) == 33.3

    def test_safe_percentage_zero_total(self) -> None:
        assert _safe_percentage(0, 0) == 0.0

    def test_calculate_mean(self) -> None:
        assert _calculate_mean([1, 2, 3]) == 2.0
        assert _calculate_mean([]) == 0.0
        assert _calculate_mean([5]) == 5.0

    def test_calculate_median(self) -> None:
        assert _calculate_median([1, 2, 3]) == 2.0
        assert _calculate_median([1, 2, 3, 4]) == 2.5
        assert _calculate_median([]) == 0.0
        assert _calculate_median([7]) == 7.0


# ─────────────────────────────────────────────────────────────────────
# 2. Unit Tests — Spearman Rank Correlation
# ─────────────────────────────────────────────────────────────────────


class TestSpearmanCorrelation:
    def test_perfect_positive_correlation(self) -> None:
        rho = _spearman_rank_correlation([1, 2, 3, 4], [1, 2, 3, 4])
        assert rho is not None
        assert abs(rho - 1.0) < 0.001

    def test_perfect_negative_correlation(self) -> None:
        rho = _spearman_rank_correlation([1, 2, 3, 4], [4, 3, 2, 1])
        assert rho is not None
        assert abs(rho - (-1.0)) < 0.001

    def test_known_correlation(self) -> None:
        # A=1,B=2,C=3,D=4 vs A=3,B=1,C=4,D=2
        rho = _spearman_rank_correlation([1, 2, 3, 4], [3, 1, 4, 2])
        assert rho is not None
        assert -1.0 <= rho <= 1.0

    def test_insufficient_data_returns_none(self) -> None:
        assert _spearman_rank_correlation([], []) is None
        assert _spearman_rank_correlation([1], [1]) is None

    def test_identical_ranks_returns_none(self) -> None:
        assert _spearman_rank_correlation([1, 1, 1], [1, 1, 1]) is None


# ─────────────────────────────────────────────────────────────────────
# 3. Unit Tests — Movement Classification
# ─────────────────────────────────────────────────────────────────────


class TestMovementClassification:
    def test_significantly_improved(self) -> None:
        assert RankingImpactAnalyzer._classify_movement(SIGNIFICANT_IMPROVEMENT_THRESHOLD) == "significantly_improved"
        assert RankingImpactAnalyzer._classify_movement(15) == "significantly_improved"

    def test_improved(self) -> None:
        assert RankingImpactAnalyzer._classify_movement(IMPROVEMENT_THRESHOLD) == "improved"
        assert RankingImpactAnalyzer._classify_movement(5) == "improved"

    def test_unchanged(self) -> None:
        assert RankingImpactAnalyzer._classify_movement(0) == "unchanged"
        assert RankingImpactAnalyzer._classify_movement(2) == "unchanged"
        assert RankingImpactAnalyzer._classify_movement(-2) == "unchanged"

    def test_declined(self) -> None:
        assert RankingImpactAnalyzer._classify_movement(DECLINE_THRESHOLD) == "declined"
        assert RankingImpactAnalyzer._classify_movement(-5) == "declined"

    def test_significantly_declined(self) -> None:
        assert RankingImpactAnalyzer._classify_movement(SIGNIFICANT_DECLINE_THRESHOLD) == "significantly_declined"
        assert RankingImpactAnalyzer._classify_movement(-15) == "significantly_declined"


# ─────────────────────────────────────────────────────────────────────
# 4. Unit Tests — Shortlist Change / Qualification Change Labels
# ─────────────────────────────────────────────────────────────────────


class TestChangeLabels:
    def test_shortlist_change_labels(self) -> None:
        from app.domain.simulation_models import SimulationResult as SR

        retained = SR(
            execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(), candidate_name="A",
            baseline_score=80, simulation_score=80, score_change=0,
            baseline_rank=1, simulation_rank=1, rank_change=0,
            baseline_status="qualified", simulation_status="qualified",
            baseline_shortlisted=True, simulation_shortlisted=True,
        )
        assert RankingImpactAnalyzer._shortlist_change_label(retained) == "retained"

        entered = SR(
            execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(), candidate_name="B",
            baseline_score=60, simulation_score=80, score_change=20,
            baseline_rank=10, simulation_rank=2, rank_change=8,
            baseline_status="not_qualified", simulation_status="qualified",
            baseline_shortlisted=False, simulation_shortlisted=True,
        )
        assert RankingImpactAnalyzer._shortlist_change_label(entered) == "entered"

        left = SR(
            execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(), candidate_name="C",
            baseline_score=80, simulation_score=60, score_change=-20,
            baseline_rank=2, simulation_rank=10, rank_change=-8,
            baseline_status="qualified", simulation_status="qualified",
            baseline_shortlisted=True, simulation_shortlisted=False,
        )
        assert RankingImpactAnalyzer._shortlist_change_label(left) == "left"

    def test_qualification_change_labels(self) -> None:
        from app.domain.simulation_models import SimulationResult as SR

        remained_qualified = SR(
            execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(), candidate_name="A",
            baseline_score=80, simulation_score=80, score_change=0,
            baseline_rank=1, simulation_rank=1, rank_change=0,
            baseline_status="qualified", simulation_status="qualified",
            baseline_shortlisted=True, simulation_shortlisted=True,
        )
        assert RankingImpactAnalyzer._qualification_change_label(remained_qualified) == "remained_qualified"

        newly_qualified = SR(
            execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(), candidate_name="B",
            baseline_score=60, simulation_score=80, score_change=20,
            baseline_rank=10, simulation_rank=2, rank_change=8,
            baseline_status="not_qualified", simulation_status="qualified",
            baseline_shortlisted=False, simulation_shortlisted=True,
        )
        assert RankingImpactAnalyzer._qualification_change_label(newly_qualified) == "newly_qualified"

        newly_disqualified = SR(
            execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(), candidate_name="C",
            baseline_score=80, simulation_score=60, score_change=-20,
            baseline_rank=2, simulation_rank=10, rank_change=-8,
            baseline_status="qualified", simulation_status="not_qualified",
            baseline_shortlisted=True, simulation_shortlisted=False,
        )
        assert RankingImpactAnalyzer._qualification_change_label(newly_disqualified) == "newly_disqualified"


# ─────────────────────────────────────────────────────────────────────
# 5. Unit Tests — Qualification Matrix Calculation
# ─────────────────────────────────────────────────────────────────────


class TestQualificationMatrix:
    def test_qualification_matrix_from_results(self) -> None:
        """Test qualification matrix with manually constructed data."""
        from app.domain.simulation_models import SimulationResult as SR

        results = [
            # A: qualified -> qualified (a)
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="A",
                baseline_score=85, simulation_score=90, score_change=5,
                baseline_rank=1, simulation_rank=1, rank_change=0,
                baseline_status="qualified", simulation_status="qualified",
                baseline_shortlisted=True, simulation_shortlisted=True,
            ),
            # B: qualified -> not_qualified (b)
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="B",
                baseline_score=75, simulation_score=50, score_change=-25,
                baseline_rank=2, simulation_rank=5, rank_change=-3,
                baseline_status="qualified", simulation_status="not_qualified",
                baseline_shortlisted=True, simulation_shortlisted=False,
            ),
            # C: not_qualified -> qualified (c)
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="C",
                baseline_score=60, simulation_score=80, score_change=20,
                baseline_rank=5, simulation_rank=2, rank_change=3,
                baseline_status="not_qualified", simulation_status="qualified",
                baseline_shortlisted=False, simulation_shortlisted=True,
            ),
            # D: not_qualified -> not_qualified (d)
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="D",
                baseline_score=40, simulation_score=45, score_change=5,
                baseline_rank=6, simulation_rank=6, rank_change=0,
                baseline_status="not_qualified", simulation_status="not_qualified",
                baseline_shortlisted=False, simulation_shortlisted=False,
            ),
        ]

        analyzer = RankingImpactAnalyzer.__new__(RankingImpactAnalyzer)
        matrix = analyzer._analyze_qualification_matrix(results)

        assert matrix.baseline_qualified_simulation_qualified == 1  # A
        assert matrix.baseline_qualified_simulation_not_qualified == 1  # B
        assert matrix.baseline_not_qualified_simulation_qualified == 1  # C
        assert matrix.baseline_not_qualified_simulation_not_qualified == 1  # D
        assert matrix.newly_qualified == 1
        assert matrix.newly_disqualified == 1
        assert matrix.remained_qualified == 1
        assert matrix.remained_unqualified == 1
        assert matrix.total_qualified_change == 0  # c - b = 1 - 1


# ─────────────────────────────────────────────────────────────────────
# 6. Unit Tests — Rank Distribution
# ─────────────────────────────────────────────────────────────────────


class TestRankDistribution:
    def test_rank_distribution_buckets(self) -> None:
        from app.domain.simulation_models import SimulationResult as SR

        results = [
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="A",
                baseline_score=90, simulation_score=90, score_change=0,
                baseline_rank=1, simulation_rank=3, rank_change=-2,
                baseline_status="qualified", simulation_status="qualified",
                baseline_shortlisted=True, simulation_shortlisted=True,
            ),
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="B",
                baseline_score=80, simulation_score=85, score_change=5,
                baseline_rank=5, simulation_rank=1, rank_change=4,
                baseline_status="qualified", simulation_status="qualified",
                baseline_shortlisted=True, simulation_shortlisted=True,
            ),
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="C",
                baseline_score=60, simulation_score=70, score_change=10,
                baseline_rank=12, simulation_rank=8, rank_change=4,
                baseline_status="not_qualified", simulation_status="qualified",
                baseline_shortlisted=False, simulation_shortlisted=True,
            ),
        ]

        analyzer = RankingImpactAnalyzer.__new__(RankingImpactAnalyzer)
        buckets = analyzer._analyze_rank_distribution(
            results,
            [("1-5", 1, 5), ("6-10", 6, 10), ("11-20", 11, 20)],
        )

        assert len(buckets.buckets) == 3
        # Baseline: A=1, B=5 -> 1-5 has 2; C=12 -> 11-20 has 1
        assert buckets.buckets[0].baseline_count == 2
        assert buckets.buckets[1].baseline_count == 0
        assert buckets.buckets[2].baseline_count == 1
        # Simulation: A=3, B=1 -> 1-5 has 2; C=8 -> 6-10 has 1
        assert buckets.buckets[0].simulation_count == 2
        assert buckets.buckets[1].simulation_count == 1
        assert buckets.buckets[2].simulation_count == 0


# ─────────────────────────────────────────────────────────────────────
# 7. Unit Tests — Score Distribution
# ─────────────────────────────────────────────────────────────────────


class TestScoreDistribution:
    def test_score_distribution_bands(self) -> None:
        from app.domain.simulation_models import SimulationResult as SR

        results = [
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="A",
                baseline_score=92, simulation_score=95, score_change=3,
                baseline_rank=1, simulation_rank=1, rank_change=0,
                baseline_status="qualified", simulation_status="qualified",
                baseline_shortlisted=True, simulation_shortlisted=True,
            ),
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="B",
                baseline_score=65, simulation_score=72, score_change=7,
                baseline_rank=3, simulation_rank=2, rank_change=1,
                baseline_status="not_qualified", simulation_status="qualified",
                baseline_shortlisted=False, simulation_shortlisted=True,
            ),
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="C",
                baseline_score=45, simulation_score=40, score_change=-5,
                baseline_rank=5, simulation_rank=5, rank_change=0,
                baseline_status="not_qualified", simulation_status="not_qualified",
                baseline_shortlisted=False, simulation_shortlisted=False,
            ),
        ]

        analyzer = RankingImpactAnalyzer.__new__(RankingImpactAnalyzer)
        dist = analyzer._analyze_score_distribution(
            results,
            [("0-49", 0, 49), ("50-69", 50, 69), ("70-89", 70, 89), ("90-100", 90, 100)],
        )

        assert len(dist.buckets) == 4
        # Baseline: 92->90-100(1), 65->50-69(1), 45->0-49(1)
        assert dist.buckets[0].baseline_count == 1  # 0-49
        assert dist.buckets[1].baseline_count == 1  # 50-69
        assert dist.buckets[2].baseline_count == 0  # 70-89
        assert dist.buckets[3].baseline_count == 1  # 90-100
        # Simulation: 95->90-100(1), 72->70-89(1), 40->0-49(1)
        assert dist.buckets[0].simulation_count == 1
        assert dist.buckets[1].simulation_count == 0
        assert dist.buckets[2].simulation_count == 1
        assert dist.buckets[3].simulation_count == 1


# ─────────────────────────────────────────────────────────────────────
# 8. Unit Tests — Empty Results
# ─────────────────────────────────────────────────────────────────────


class TestEmptyResults:
    def test_empty_results_returns_valid_empty_response(self) -> None:
        """Verify the analyzer returns valid structures for zero candidates."""
        from app.domain.simulation_models import SimulationResult as SR

        analyzer = RankingImpactAnalyzer.__new__(RankingImpactAnalyzer)
        results: list[SR] = []

        overview = analyzer._analyze_overview(results)
        assert overview.total_candidates == 0
        assert overview.candidates_moved_up == 0
        assert overview.candidates_moved_down == 0
        assert overview.candidates_unchanged == 0

        score_movement = analyzer._analyze_score_movement(results)
        assert score_movement.positive_change_count == 0
        assert score_movement.negative_change_count == 0
        assert score_movement.unchanged_count == 0

        shortlist = analyzer._analyze_shortlist_impact(results)
        assert shortlist.baseline_size == 0
        assert shortlist.simulation_size == 0
        assert shortlist.jaccard_similarity == 0.0
        assert shortlist.retention_rate == 0.0

        matrix = analyzer._analyze_qualification_matrix(results)
        assert matrix.newly_qualified == 0
        assert matrix.newly_disqualified == 0

        stability = analyzer._analyze_rank_stability(results)
        assert stability.rank_stability == 0.0
        assert stability.rank_correlation is None

        insights = analyzer._generate_insights(
            overview, shortlist, matrix, stability, score_movement, [],
        )
        assert insights == []


# ─────────────────────────────────────────────────────────────────────
# 9. Unit Tests — Shortlist Impact Calculation
# ─────────────────────────────────────────────────────────────────────


class TestShortlistImpactCalculation:
    def test_shortlist_overlap_and_retention(self) -> None:
        from app.domain.simulation_models import SimulationResult as SR

        cid1, cid2, cid3, cid4 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()

        results = [
            # Baseline shortlisted: cid1, cid2, cid3
            # Simulation shortlisted: cid1, cid2, cid4
            # Retained: cid1, cid2 (overlap=2)
            # Left: cid3 (1)
            # Entered: cid4 (1)
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=cid1, candidate_name="A",
                baseline_score=90, simulation_score=92, score_change=2,
                baseline_rank=1, simulation_rank=1, rank_change=0,
                baseline_status="qualified", simulation_status="qualified",
                baseline_shortlisted=True, simulation_shortlisted=True,
            ),
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=cid2, candidate_name="B",
                baseline_score=85, simulation_score=87, score_change=2,
                baseline_rank=2, simulation_rank=2, rank_change=0,
                baseline_status="qualified", simulation_status="qualified",
                baseline_shortlisted=True, simulation_shortlisted=True,
            ),
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=cid3, candidate_name="C",
                baseline_score=80, simulation_score=60, score_change=-20,
                baseline_rank=3, simulation_rank=5, rank_change=-2,
                baseline_status="qualified", simulation_status="not_qualified",
                baseline_shortlisted=True, simulation_shortlisted=False,
            ),
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=cid4, candidate_name="D",
                baseline_score=50, simulation_score=82, score_change=32,
                baseline_rank=5, simulation_rank=3, rank_change=2,
                baseline_status="not_qualified", simulation_status="qualified",
                baseline_shortlisted=False, simulation_shortlisted=True,
            ),
        ]

        analyzer = RankingImpactAnalyzer.__new__(RankingImpactAnalyzer)
        impact = analyzer._analyze_shortlist_impact(results)

        assert impact.baseline_size == 3
        assert impact.simulation_size == 3
        assert impact.candidates_retained == 2
        assert impact.candidates_entering == 1
        assert impact.candidates_leaving == 1
        assert impact.overlap_count == 2
        # Jaccard = overlap / union = 2 / 4 = 0.5
        assert abs(impact.jaccard_similarity - 0.5) < 0.001
        # Retention = overlap / baseline = 2 / 3
        assert abs(impact.retention_rate - (2 / 3)) < 0.001
        assert impact.expansion_count == 0


# ─────────────────────────────────────────────────────────────────────
# 10. Unit Tests — Top Movers Deterministic Ordering
# ─────────────────────────────────────────────────────────────────────


class TestTopMovers:
    def test_top_movers_deterministic_ordering(self) -> None:
        from app.domain.simulation_models import SimulationResult as SR

        results = [
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="Zoe",
                baseline_score=50, simulation_score=80, score_change=30,
                baseline_rank=5, simulation_rank=1, rank_change=4,
                baseline_status="not_qualified", simulation_status="qualified",
                baseline_shortlisted=False, simulation_shortlisted=True,
            ),
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="Alice",
                baseline_score=60, simulation_score=90, score_change=30,
                baseline_rank=4, simulation_rank=1, rank_change=3,
                baseline_status="not_qualified", simulation_status="qualified",
                baseline_shortlisted=False, simulation_shortlisted=True,
            ),
        ]

        analyzer = RankingImpactAnalyzer.__new__(RankingImpactAnalyzer)
        upward = analyzer._top_movers(results, direction="up", limit=5)

        assert len(upward) == 2
        # Zoe has rank_change=4, Alice has rank_change=3
        # But when rank_changes are equal (3 vs 4), Zoe (4) comes first
        assert upward[0].candidate_name == "Zoe"
        assert upward[0].rank_change == 4
        assert upward[1].candidate_name == "Alice"
        assert upward[1].rank_change == 3

    def test_top_movers_limit(self) -> None:
        from app.domain.simulation_models import SimulationResult as SR

        results = [
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name=f"Candidate{i}",
                baseline_score=50, simulation_score=50 + i, score_change=i,
                baseline_rank=10, simulation_rank=10 - i, rank_change=i,
                baseline_status="not_qualified", simulation_status="not_qualified",
                baseline_shortlisted=False, simulation_shortlisted=False,
            )
            for i in range(1, 11)
        ]

        analyzer = RankingImpactAnalyzer.__new__(RankingImpactAnalyzer)
        upward = analyzer._top_movers(results, direction="up", limit=3)
        assert len(upward) == 3
        # Highest rank_change first
        assert upward[0].rank_change == 10
        assert upward[1].rank_change == 9
        assert upward[2].rank_change == 8


# ─────────────────────────────────────────────────────────────────────
# 11. Unit Tests — Threshold Impact
# ─────────────────────────────────────────────────────────────────────


class TestThresholdImpact:
    def test_threshold_impact_increased(self) -> None:
        from app.domain.simulation_models import SimulationResult as SR

        results = [
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="A",
                baseline_score=75, simulation_score=80, score_change=5,
                baseline_rank=1, simulation_rank=1, rank_change=0,
                baseline_status="qualified", simulation_status="qualified",
                baseline_shortlisted=True, simulation_shortlisted=True,
            ),
            SR(
                execution_id=uuid.uuid4(), scenario_id=uuid.uuid4(),
                candidate_id=uuid.uuid4(), candidate_name="B",
                baseline_score=65, simulation_score=70, score_change=5,
                baseline_rank=2, simulation_rank=2, rank_change=0,
                baseline_status="not_qualified", simulation_status="qualified",
                baseline_shortlisted=False, simulation_shortlisted=False,
            ),
        ]

        analyzer = RankingImpactAnalyzer.__new__(RankingImpactAnalyzer)
        impact = analyzer._analyze_threshold_impact(
            results,
            {"threshold": 70},
            {"threshold": 65},
        )

        assert impact.baseline_threshold == 70
        assert impact.simulation_threshold == 65
        assert impact.baseline_qualified_count == 1  # A (75 >= 70)
        assert impact.simulation_qualified_count == 2  # A (80 >= 65), B (70 >= 65)
        assert impact.qualified_change == 1
        assert "more" in impact.description


# ─────────────────────────────────────────────────────────────────────
# 12. Integration Tests — Full API Lifecycle
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ranking_impact_api_returns_completed_results(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Impact Org", f"impact-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    pool = await _seed_default_pool(session, job)
    scenario = await _create_scenario_via_api(client, token, job, "Impact Test", SIM_CONFIG)

    # Run the simulation
    run_resp = await client.post(
        f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token),
    )
    assert run_resp.status_code == 202, run_resp.text
    assert run_resp.json()["status"] == "completed"

    # Get ranking impact
    impact_resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/ranking-impact", headers=_auth(token),
    )
    assert impact_resp.status_code == 200, impact_resp.text
    data = impact_resp.json()

    assert data["simulation_id"] == scenario["id"]
    assert data["execution_status"] == "completed"
    assert data["overview"]["total_candidates"] == 3
    assert data["overview"]["candidates_moved_up"] + data["overview"]["candidates_moved_down"] + data["overview"]["candidates_unchanged"] == 3

    assert data["shortlist_impact"]["baseline_size"] >= 0
    assert data["shortlist_impact"]["simulation_size"] >= 0

    assert data["qualification_matrix"]["baseline_qualified_simulation_qualified"] >= 0
    assert data["qualification_matrix"]["newly_qualified"] >= 0
    assert data["qualification_matrix"]["newly_disqualified"] >= 0

    assert len(data["rank_distribution"]["buckets"]) > 0
    assert len(data["score_distribution"]["buckets"]) > 0

    assert isinstance(data["rank_stability"]["rank_stability"], float)
    assert data["insights"] is not None


@pytest.mark.asyncio
async def test_ranking_impact_candidates_endpoint(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Cand Org", f"cand-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    await _seed_default_pool(session, job)
    scenario = await _create_scenario_via_api(client, token, job, "Cand Test", SIM_CONFIG)
    await client.post(f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token))

    # Get candidate impact list
    resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/ranking-impact/candidates",
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total"] == 3
    assert len(data["items"]) == 3
    assert all("movement_category" in item for item in data["items"])
    assert all("shortlist_change" in item for item in data["items"])
    assert all("qualification_change" for item in data["items"])


@pytest.mark.asyncio
async def test_ranking_impact_single_candidate_endpoint(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Single Org", f"single-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    pool = await _seed_default_pool(session, job)
    scenario = await _create_scenario_via_api(client, token, job, "Single Test", SIM_CONFIG)
    await client.post(f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token))

    # Get single candidate impact
    alice_id = str(pool["alice"].id)
    resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/ranking-impact/candidates/{alice_id}",
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["candidate"]["candidate_id"] == alice_id
    assert "baseline" in data
    assert "simulation" in data
    assert "changes" in data
    assert "explanation" in data
    assert len(data["explanation"]) > 0


@pytest.mark.asyncio
async def test_ranking_impact_empty_pool(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Empty Org", f"empty-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    scenario = await _create_scenario_via_api(client, token, job, "Empty Test", SIM_CONFIG)
    await client.post(f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token))

    resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/ranking-impact", headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["overview"]["total_candidates"] == 0


@pytest.mark.asyncio
async def test_ranking_impact_with_execution_id(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Exec Org", f"exec-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    await _seed_default_pool(session, job)
    scenario = await _create_scenario_via_api(client, token, job, "Exec Test", SIM_CONFIG)
    run_resp = await client.post(
        f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token),
    )
    execution_id = run_resp.json()["id"]

    # Explicit execution_id
    resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/ranking-impact?execution_id={execution_id}",
        headers=_auth(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["execution_id"] == execution_id


# ─────────────────────────────────────────────────────────────────────
# 13. RBAC + Tenant Isolation
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ranking_impact_rbac_and_tenant_isolation(
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

    # Tenant B cannot access Tenant A's ranking impact
    resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/ranking-impact", headers=_auth(token_b),
    )
    assert resp.status_code == 403

    resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/ranking-impact/candidates", headers=_auth(token_b),
    )
    assert resp.status_code == 403

    # Candidate role cannot access
    candidate = User(
        id=uuid.uuid4(), full_name="Cand",
        email=f"cand_{uuid.uuid4().hex[:6]}@test.com", password_hash=hash_password(PASSWORD), is_active=True,
    )
    session.add(candidate)
    await session.flush()
    cand_token = await _login(client, candidate.email)
    resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/ranking-impact", headers=_auth(cand_token),
    )
    assert resp.status_code == 403


# ─────────────────────────────────────────────────────────────────────
# 14. CRITICAL Regression — No Live Hiring Data Modified
# ─────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ranking_impact_never_modifies_live_hiring_data(
    session: AsyncSession, client: AsyncClient,
) -> None:
    org = await _create_org(session, "Safe Org", f"safe-{uuid.uuid4().hex[:6]}")
    recruiter, token = await _setup_recruiter_with_org(session, client, org)
    job = await _create_job(session, recruiter, org)
    await _seed_default_pool(session, job)
    scenario = await _create_scenario_via_api(client, token, job, "Safe", SIM_CONFIG)

    # Run simulation first
    run_resp = await client.post(
        f"/api/v1/simulations/{scenario['id']}/run", headers=_auth(token),
    )
    assert run_resp.json()["status"] == "completed"

    # Snapshot before impact analysis
    job_cols = [
        Job.title, Job.description, Job.location, Job.employment_type,
        Job.required_skills, Job.preferred_skills, Job.version, Job.status,
    ]
    before_job = (await session.execute(select(*job_cols).where(Job.id == job.id))).one()
    before_rankings = (await session.execute(select(func.count()).select_from(CandidateRanking))).scalar()
    before_screenings = (await session.execute(select(func.count()).select_from(ScreeningResult))).scalar()

    # Run impact analysis
    resp = await client.get(
        f"/api/v1/simulations/{scenario['id']}/ranking-impact", headers=_auth(token),
    )
    assert resp.status_code == 200

    # Verify no live data was modified
    after_job = (await session.execute(select(*job_cols).where(Job.id == job.id))).one()
    assert before_job == after_job, "Job row was modified by impact analysis!"

    after_rankings = (await session.execute(select(func.count()).select_from(CandidateRanking))).scalar()
    after_screenings = (await session.execute(select(func.count()).select_from(ScreeningResult))).scalar()
    assert before_rankings == after_rankings, "Impact analysis modified CandidateRanking!"
    assert before_screenings == after_screenings, "Impact analysis modified ScreeningResult!"
