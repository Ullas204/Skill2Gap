"""Phase 2 Skill2Job detail endpoints tests.

Covers the explainable extensions built on the existing catalog, matching,
gap and skill-graph engines:
- job detail endpoint
- dataset-wide skill demand aggregation
- per-job match detail (categories + per-skill evidence states)
- per-job gap detail (skill gap vs evidence gap)
- job-centric skill graph
"""

import pytest
from httpx import AsyncClient


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Phase2 Candidate", "email": email, "password": password},
    )
    assert resp.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


RESUME_TEXT = b"""Neha Iyer
Chennai, India | neha.iyer@example.com

SKILLS
JavaScript, React, HTML, CSS, Git

EXPERIENCE
Frontend Developer | PixelWorks | Remote
Mar 2021 - Present
Built React dashboards and component libraries.

EDUCATION
B.Sc Computer Science, Loyola College, 2017 - 2020
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


@pytest.mark.asyncio
async def test_job_detail_returns_full_record(client: AsyncClient):
    tokens = await _register_and_login(client, "detail@test.com")
    headers = _headers(tokens)
    job_id = await _first_job_id(client, headers)

    resp = await client.get(f"/api/v1/skill2job/jobs/{job_id}", headers=headers)
    assert resp.status_code == 200
    job = resp.json()
    assert job["id"] == job_id
    for key in ("title", "company", "description", "required_skills", "preferred_skills"):
        assert key in job
    assert job["required_skills"], "expected at least one required skill"


@pytest.mark.asyncio
async def test_job_detail_404_for_unknown(client: AsyncClient):
    tokens = await _register_and_login(client, "detail_404@test.com")
    headers = _headers(tokens)
    resp = await client.get(
        "/api/v1/skill2job/jobs/00000000-0000-0000-0000-000000000000", headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_skill_demand_aggregates_dataset(client: AsyncClient):
    tokens = await _register_and_login(client, "demand@test.com")
    headers = _headers(tokens)
    resp = await client.get("/api/v1/skill2job/skills/demand", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["dataset"].startswith("skill2job-curated-jobs")
    assert body["total_jobs"] >= 40
    assert body["items"], "expected at least one demanded skill"
    top = body["items"][0]
    assert top["count"] >= top["required_count"]
    assert top["demand_level"] in ("high", "medium", "low")
    assert top["jobs_demanding"], "expected at least one demanding job title"


@pytest.mark.asyncio
async def test_job_match_detail_is_explainable(client: AsyncClient):
    tokens = await _register_and_login(client, "match_detail@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)
    job_id = await _first_job_id(client, headers)

    await client.post("/api/v1/skill2job/jobs/match", json={"job_ids": [job_id], "limit": 1}, headers=headers)

    resp = await client.get(f"/api/v1/skill2job/jobs/{job_id}/match", headers=headers)
    assert resp.status_code == 200
    detail = resp.json()
    assert detail["job_id"] == job_id
    assert detail["category"] in ("matched", "partial", "missing", "unknown")
    assert detail["categories_explained"]
    assert detail["match_version"].startswith("skill2job-match")
    assert 0 <= detail["overall_score"] <= 100
    assert {*detail["scores"]} >= {"skill", "experience", "education", "semantic"}
    assert detail["explanation"], "expected a grounded explanation"
    assert detail["skill_details"], "expected per-skill detail"
    required = [
        sd
        for sd in detail["skill_details"]
        if sd["kind"] == "required"
    ]
    assert required, "expected required skills in the detail"
    for sd in required[:3]:
        assert sd["status"] in ("matched", "transferable", "missing")
        assert sd["evidence_state"] in ("claimed", "supported", "demonstrated", "verified", "none")
    reasons_found = {sd["skill"].lower() for sd in required}
    assert detail["missing_required"] or any(s in reasons_found for s in detail["matched_skills"])


@pytest.mark.asyncio
async def test_job_match_detail_404_for_unknown(client: AsyncClient):
    tokens = await _register_and_login(client, "match_detail_404@test.com")
    headers = _headers(tokens)
    resp = await client.get(
        "/api/v1/skill2job/jobs/00000000-0000-0000-0000-000000000000/match", headers=headers
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_job_gap_detail_classifies_gap_kind(client: AsyncClient):
    tokens = await _register_and_login(client, "gap_detail@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)
    job_id = await _first_job_id(client, headers)

    resp = await client.get(f"/api/v1/skill2job/jobs/{job_id}/gaps", headers=headers)
    assert resp.status_code == 200
    gap = resp.json()
    assert gap["job_id"] == job_id
    assert gap["analysis_version"].startswith("skill2job-gap")
    assert 0 <= gap["interview_readiness_score"] <= 100
    for item in gap["gap_items"]:
        assert item["gap_kind"] in ("skill_gap", "evidence_gap")
        assert item["evidence_note"]
        assert item["priority"] in ("high", "medium", "low")


@pytest.mark.asyncio
async def test_job_skill_graph_is_job_centric(client: AsyncClient):
    tokens = await _register_and_login(client, "job_graph@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)
    job_id = await _first_job_id(client, headers)

    resp = await client.get(f"/api/v1/skill2job/jobs/{job_id}/graph", headers=headers)
    assert resp.status_code == 200
    graph = resp.json()
    assert graph["job"]["id"] == job_id
    kinds = {n["kind"] for n in graph["nodes"]}
    assert "job" in kinds
    assert graph["nodes"] and graph["edges"]
    assert graph["generated_from"]["job_skills"] >= 1


@pytest.mark.asyncio
async def test_detail_endpoints_require_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Phase2", "rec_phase2@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    headers = _headers(login.json())
    assert (await client.get("/api/v1/skill2job/skills/demand", headers=headers)).status_code == 403
    assert (
        await client.get(
            "/api/v1/skill2job/jobs/00000000-0000-0000-0000-000000000000", headers=headers
        )
    ).status_code == 403