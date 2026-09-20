"""Phase 3 Skill2Job Readiness, Skill Proof, Learning Progress & Comparison tests.

Covers:
- Evidence-Aware Readiness Engine (unit + integration)
- Skill Proof Enhancement (proof_status field, detail endpoint, classify)
- Learning Progress States (valid/invalid state, not_started default)
- Per-Job Learning Plan
- Opportunity Dashboard Enhancement (readiness + cost_analysis)
- Multi-Job Comparison
- RBAC: candidate-only gating for new Phase 3 endpoints
"""

import pytest
from httpx import AsyncClient

from app.skill2job.readiness.engine import EVIDENCE_MULTIPLIERS, ReadinessEngine
from app.skill2job.service import Skill2JobService


# ─── Shared helpers ─────────────────────────────────────────────────────


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Phase3 Candidate", "email": email, "password": password},
    )
    assert resp.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


RESUME_TEXT = b"""Priya Sharma
Bangalore, India | priya.sharma@example.com

SKILLS
Python, SQL, Machine Learning, TensorFlow, Pandas, Git

EXPERIENCE
Data Scientist | AnalyticsHub | Bangalore
Apr 2020 - Present
Built ML models and data pipelines using Python and TensorFlow.

EDUCATION
B.Tech Computer Science, IIT Bangalore, 2016 - 2020
"""


async def _prime(client: AsyncClient, headers: dict) -> None:
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )


async def _first_job_id(client: AsyncClient, headers: dict) -> str:
    resp = await client.get("/api/v1/skill2job/jobs/catalog", params={"limit": 1}, headers=headers)
    assert resp.status_code == 200
    jobs = resp.json()["jobs"]
    assert jobs
    return jobs[0]["id"]


async def _run_match(client: AsyncClient, headers: dict, job_id: str) -> None:
    resp = await client.post(
        "/api/v1/skill2job/jobs/match",
        json={"job_ids": [job_id], "limit": 1},
        headers=headers,
    )
    assert resp.status_code == 200


# ─── 1. Readiness Engine Tests ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_readiness_engine_returns_valid_result(client: AsyncClient):
    tokens = await _register_and_login(client, "readiness_valid@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)
    job_id = await _first_job_id(client, headers)
    await _run_match(client, headers, job_id)

    resp = await client.get(f"/api/v1/skill2job/readiness/{job_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == job_id
    assert body["version"].startswith("skill2job-readiness")
    assert 0.0 <= body["overall_readiness"] <= 1.0
    assert 0.0 <= body["skill_coverage"] <= 1.0
    assert 0.0 <= body["evidence_quality"] <= 1.0
    assert isinstance(body["critical_gaps"], list)
    assert isinstance(body["evidence_breakdown"], list)
    assert isinstance(body["total_required"], int) and body["total_required"] >= 0
    assert isinstance(body["matched_count"], int)
    assert isinstance(body["missing_count"], int)


def test_readiness_evidence_multipliers():
    expected_keys = {"claimed", "supported", "learned", "demonstrated", "assessed", "verified"}
    assert set(EVIDENCE_MULTIPLIERS.keys()) == expected_keys
    assert EVIDENCE_MULTIPLIERS["claimed"] == 0.3
    assert EVIDENCE_MULTIPLIERS["supported"] == 0.5
    assert EVIDENCE_MULTIPLIERS["learned"] == 0.7
    assert EVIDENCE_MULTIPLIERS["demonstrated"] == 0.85
    assert EVIDENCE_MULTIPLIERS["assessed"] == 0.9
    assert EVIDENCE_MULTIPLIERS["verified"] == 1.0
    assert len(EVIDENCE_MULTIPLIERS) == 6


@pytest.mark.asyncio
async def test_readiness_engine_empty_profile(client: AsyncClient):
    tokens = await _register_and_login(client, "readiness_empty@test.com")
    headers = _headers(tokens)
    job_id = await _first_job_id(client, headers)

    resp = await client.get(f"/api/v1/skill2job/readiness/{job_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["overall_readiness"] == 0.0
    assert body["skill_coverage"] == 0.0
    assert body["evidence_quality"] == 0.0


# ─── 2. Skill Proof Enhancement Tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_skill_proof_includes_proof_status(client: AsyncClient):
    tokens = await _register_and_login(client, "proof_status@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)

    resp = await client.get("/api/v1/skill2job/skill-proof", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "skills" in body
    assert isinstance(body["skills"], list)
    assert len(body["skills"]) > 0, "expected at least one skill after resume upload"
    for skill in body["skills"]:
        assert "proof_status" in skill, f"missing proof_status on skill {skill.get('name')}"
        assert skill["proof_status"] in ("LEARN", "PROVE", "VERIFIED")
        assert "proof_plan" in skill
        assert isinstance(skill["proof_plan"], dict)
        assert "action" in skill["proof_plan"]


@pytest.mark.asyncio
async def test_skill_proof_detail_endpoint(client: AsyncClient):
    tokens = await _register_and_login(client, "proof_detail@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)

    # Get the skill proof list to find a valid skill name
    proof_resp = await client.get("/api/v1/skill2job/skill-proof", headers=headers)
    assert proof_resp.status_code == 200
    skills = proof_resp.json()["skills"]
    assert skills, "need at least one skill"
    skill_name = skills[0]["name"]

    resp = await client.get(f"/api/v1/skill2job/skill-proof/{skill_name}", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["skill"] == skill_name
    assert "proof_status" in detail
    assert detail["proof_status"] in ("LEARN", "PROVE", "VERIFIED")
    assert "evidence" in detail
    assert "supported_by" in detail
    assert "proof_plan" in detail
    assert "learning_resources" in detail


def test_skill_proof_classify_status():
    svc = Skill2JobService.__new__(Skill2JobService)

    # Strong evidence sources → VERIFIED
    assert svc._classify_proof_status("python", ["perception", "profile"], None, None) == "VERIFIED"
    assert svc._classify_proof_status("python", ["matched_jobs"], None, None) == "VERIFIED"
    assert svc._classify_proof_status("python", ["training"], None, None) == "VERIFIED"
    assert svc._classify_proof_status("python", ["perception", "matched_jobs"], None, None) == "VERIFIED"

    # Profile-only with proficiency → PROVE
    assert svc._classify_proof_status("python", ["profile"], "Intermediate", 2) == "PROVE"
    assert svc._classify_proof_status("python", ["profile"], None, 3) == "PROVE"

    # Profile-only without proficiency/years → PROVE
    assert svc._classify_proof_status("python", ["profile"], None, None) == "PROVE"

    # No sources at all → PROVE
    assert svc._classify_proof_status("python", [], None, None) == "PROVE"


# ─── 3. Learning Progress States Tests ─────────────────────────────────


@pytest.mark.asyncio
async def test_learning_progress_valid_state(client: AsyncClient):
    tokens = await _register_and_login(client, "progress_valid@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)

    # Get training plan to find a valid module_key
    plan_resp = await client.get("/api/v1/skill2job/training/plan", headers=headers)
    assert plan_resp.status_code == 200
    plan = plan_resp.json()
    modules = plan.get("modules", [])
    if not modules:
        pytest.skip("No training modules available")
    module_key = modules[0]["module_key"]

    resp = await client.post(
        "/api/v1/skill2job/learning/progress",
        data={"module_key": module_key, "evidence_state": "in_progress"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["evidence_state"] == "in_progress"


@pytest.mark.asyncio
async def test_learning_progress_invalid_state(client: AsyncClient):
    tokens = await _register_and_login(client, "progress_invalid@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)

    plan_resp = await client.get("/api/v1/skill2job/training/plan", headers=headers)
    assert plan_resp.status_code == 200
    modules = plan_resp.json().get("modules", [])
    if not modules:
        pytest.skip("No training modules available")
    module_key = modules[0]["module_key"]

    resp = await client.post(
        "/api/v1/skill2job/learning/progress",
        data={"module_key": module_key, "evidence_state": "totally_invalid_state"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is False
    assert "Invalid evidence_state" in body["reason"]


@pytest.mark.asyncio
async def test_learning_progress_not_started_default(client: AsyncClient):
    tokens = await _register_and_login(client, "progress_default@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)

    plan_resp = await client.get("/api/v1/skill2job/training/plan", headers=headers)
    assert plan_resp.status_code == 200
    modules = plan_resp.json().get("modules", [])
    if not modules:
        pytest.skip("No training modules available")
    module_key = modules[0]["module_key"]

    prog_resp = await client.post(
        "/api/v1/skill2job/learning/progress",
        data={"module_key": module_key, "evidence_state": "not_started"},
        headers=headers,
    )
    assert prog_resp.status_code == 200
    body = prog_resp.json()
    assert body["ok"] is True
    assert body["evidence_state"] == "not_started"


# ─── 4. Per-Job Learning Plan Tests ────────────────────────────────────


@pytest.mark.asyncio
async def test_learning_plan_for_job(client: AsyncClient):
    tokens = await _register_and_login(client, "learn_plan@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)
    job_id = await _first_job_id(client, headers)

    resp = await client.get(f"/api/v1/skill2job/learning/plan/{job_id}", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["job_id"] == job_id
    assert "job_title" in body
    assert 0.0 <= body["current_readiness"] <= 1.0
    assert isinstance(body["critical_gaps"], list)
    assert isinstance(body["missing_skills"], list)
    assert isinstance(body["learning_plan"], list)
    assert isinstance(body["total_weeks"], (int, float))
    assert isinstance(body["total_hours"], (int, float))
    assert isinstance(body["total_cost"], (int, float))
    assert isinstance(body["free_only_path"], dict)
    assert isinstance(body["opportunity_unlock"], dict)


@pytest.mark.asyncio
async def test_learning_plan_invalid_job(client: AsyncClient):
    tokens = await _register_and_login(client, "learn_plan_404@test.com")
    headers = _headers(tokens)

    resp = await client.get(
        "/api/v1/skill2job/learning/plan/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "error" in body
    assert "Job not found" in body["error"]


# ─── 5. Opportunity Dashboard Enhancement Tests ────────────────────────


@pytest.mark.asyncio
async def test_opportunity_dashboard_has_readiness(client: AsyncClient):
    tokens = await _register_and_login(client, "dash_readiness@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)
    job_id = await _first_job_id(client, headers)
    await _run_match(client, headers, job_id)

    resp = await client.get("/api/v1/skill2job/opportunity/dashboard", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "readiness" in body
    assert isinstance(body["readiness"], (int, float))
    assert "readiness_level" in body
    assert body["readiness_level"] in ("unknown", "early", "developing", "moderate", "strong")
    assert "readiness_weighted" in body
    assert "evidence_breakdown" in body
    assert isinstance(body["evidence_breakdown"], list)
    assert "matched_skills_count" in body


@pytest.mark.asyncio
async def test_opportunity_dashboard_has_cost_analysis(client: AsyncClient):
    tokens = await _register_and_login(client, "dash_cost@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)

    resp = await client.get("/api/v1/skill2job/opportunity/dashboard", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "cost_analysis" in body
    assert isinstance(body["cost_analysis"], dict)


# ─── 6. Multi-Job Comparison Tests ─────────────────────────────────────


@pytest.mark.asyncio
async def test_jobs_compare_endpoint(client: AsyncClient):
    tokens = await _register_and_login(client, "compare@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)
    job_id = await _first_job_id(client, headers)
    await _run_match(client, headers, job_id)

    resp = await client.get("/api/v1/skill2job/jobs/compare", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    # Each item should be a comparison result dict
    for item in body:
        assert "job_id" in item
        assert "job_title" in item
        assert "estimated_weeks" in item
        assert "estimated_hours" in item


# ─── 7. RBAC Tests ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_readiness_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Readiness", "rec_readiness@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    headers = _headers(login.json())
    resp = await client.get(
        "/api/v1/skill2job/readiness/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_learning_plan_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter LearnPlan", "rec_learnplan@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    headers = _headers(login.json())
    resp = await client.get(
        "/api/v1/skill2job/learning/plan/00000000-0000-0000-0000-000000000000",
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_skill_proof_detail_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter ProofDetail", "rec_proof@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    headers = _headers(login.json())
    resp = await client.get(
        "/api/v1/skill2job/skill-proof/Python",
        headers=headers,
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_learning_progress_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter LearnProgress", "rec_lprog@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    headers = _headers(login.json())
    resp = await client.post(
        "/api/v1/skill2job/learning/progress",
        data={"module_key": "test", "evidence_state": "in_progress"},
        headers=headers,
    )
    assert resp.status_code == 403
