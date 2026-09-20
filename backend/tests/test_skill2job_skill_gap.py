"""Phase 6 Skill2Job Skill Gap Agent tests.

Covers:
- provenance-annotated gap items built from persisted match outputs
- teaching plan with transfer-aware rationale (grounded, no fabrication)
- stored analysis retrieval
- aggregated summary endpoint
- candidate-only authorization
"""

import pytest
from httpx import AsyncClient


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Gap Candidate", "email": email, "password": password},
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


@pytest.mark.asyncio
async def test_analyze_builds_provenance_gaps(client: AsyncClient):
    tokens = await _register_and_login(client, "gap_analyze@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)

    resp = await client.post(
        "/api/v1/skill2job/skillgap/analyze",
        json={"limit": 3},
        headers=headers,
    )
    assert resp.status_code == 200
    analyses = resp.json()
    assert len(analyses) <= 3
    assert analyses, "expected at least one analysis"

    first = analyses[0]
    assert first["job_title"] and first["company"]
    assert 0 <= first["overall_score"] <= 100
    assert first["analysis_version"].startswith("skill2job-gap")
    # gaps only derived from the matching engine, and none are already-known skills
    known = {"javascript", "react", "html", "css", "git"}
    for item in first["gap_items"]:
        assert item["skill"].lower() not in known
        assert item["evidence"].startswith("'")
        assert "required skill for" in item["evidence"]
    assert isinstance(first["improvement_suggestions"], list)


@pytest.mark.asyncio
async def test_analysis_persists_and_retrieves(client: AsyncClient):
    tokens = await _register_and_login(client, "gap_persist@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)

    await client.post(
        "/api/v1/skill2job/skillgap/analyze",
        json={"job_ids": [await first_job_id(client, headers)]},
        headers=headers,
    )
    stored = await client.get("/api/v1/skill2job/skillgap/analyze", headers=headers)
    assert stored.status_code == 200
    body = stored.json()
    assert body and body[0]["job_title"]


@pytest.mark.asyncio
async def test_summary_aggregates_gap_skills_with_teaching_plan(client: AsyncClient):
    tokens = await _register_and_login(client, "gap_summary@test.com")
    headers = _headers(tokens)
    await _prime(client, headers)

    await client.post("/api/v1/skill2job/skillgap/analyze", json={"limit": 3}, headers=headers)
    resp = await client.get("/api/v1/skill2job/skillgap/summary", headers=headers)
    assert resp.status_code == 200
    summary = resp.json()
    assert summary["analyzed_jobs"] >= 1
    assert summary["gap_skills"], "expected at least one gap skill"
    top = summary["gap_skills"][0]
    assert top["count"] >= 1 and top["jobs_demanding"]
    plan = summary["teaching_plan"]
    assert plan and plan[0]["priority"] in ("high", "medium", "low")
    assert "rationale" in plan[0] and plan[0]["jobs_demanding"]


@pytest.mark.asyncio
async def test_skill_gap_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Gap", "rec_gap@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    resp = await client.post(
        "/api/v1/skill2job/skillgap/analyze",
        json={"limit": 1},
        headers=_headers(login.json()),
    )
    assert resp.status_code == 403


async def first_job_id(client: AsyncClient, headers: dict) -> str:
    catalog = (await client.get(
        "/api/v1/skill2job/jobs/catalog", params={"keyword": "frontend"}, headers=headers
    )).json()
    return catalog["jobs"][0]["id"]