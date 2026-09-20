"""Phase 9 Skill2Job Opportunity Impact tests.

Covers:
- per-skill impact is grounded in the candidate's matched feed
- in-memory only: no Skill2JobSimulation rows are ever written
- deterministic ordering and honest metadata (unverified effort = None)
- candidate-only authorization
"""

import pytest
from httpx import AsyncClient


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Impact Candidate", "email": email, "password": password},
    )
    assert resp.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


RESUME_TEXT = b"""Ravi Kumar
Pune, India | ravi.kumar@example.com

SKILLS
SQL, Excel, Tableau, Python

EXPERIENCE
Data Analyst | MetricsHive | Pune
Jun 2021 - Present
Built dashboards and wrote SQL analyses.

EDUCATION
B.Com, Pune University, 2017 - 2020
"""


@pytest.mark.asyncio
async def test_impact_is_grounded_and_deterministic(client: AsyncClient):
    tokens = await _register_and_login(client, "impact_det@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )

    resp = await client.get("/api/v1/skill2job/opportunity/impact", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == "skill2job-impact-1.0.0"
    assert body["threshold"] == 80
    assert body["analysis_jobs"] > 0
    assert body["total_gaps"] == len(body["skills"])
    assert body["skills"], "a resume against the curated catalog must produce gaps"

    for it in body["skills"]:
        assert it["skill"]
        assert it["unlock_potential"] >= 0
        assert it["improved_jobs"] >= 0
        assert 0.0 <= it["avg_uplift"] <= 100.0
        assert it["priority"] in {"high", "medium", "low"}
        assert it["effort_hours"] is None or it["effort_hours"] > 0
        assert isinstance(it["has_free_resource"], bool)
        assert isinstance(it["dependencies"], list)
        assert len(set(it["jobs_required"])) == len(it["jobs_required"])
        if it["demand_count"] > 0:
            assert len(it["jobs_required"]) == min(it["demand_count"], 20)

    assert body["total_unlock_potential"] == sum(
        it["unlock_potential"] for it in body["skills"]
    )
    assert body["gaps_with_unlock"] == sum(
        1 for it in body["skills"] if it["unlock_potential"] > 0
    )

    # deterministic ordering: unlock desc, demand desc, uplift desc, name asc
    keys = [
        (it["unlock_potential"], it["demand_count"], it["avg_uplift"])
        for it in body["skills"]
    ]
    assert keys == sorted(keys, key=lambda k: (-k[0], -k[1], -k[2]))

    twice = await client.get("/api/v1/skill2job/opportunity/impact", headers=headers)
    assert twice.json()["skills"] == body["skills"]


@pytest.mark.asyncio
async def test_impact_never_persists_simulations(client: AsyncClient):
    tokens = await _register_and_login(client, "impact_nopersist@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )

    resp = await client.get("/api/v1/skill2job/opportunity/impact", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["skills"]

    history = await client.get(
        "/api/v1/skill2job/opportunity/simulations", headers=headers
    )
    assert history.status_code == 200
    assert history.json()["total"] == 0


@pytest.mark.asyncio
async def test_impact_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Impact", "rec_impact@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    resp = await client.get(
        "/api/v1/skill2job/opportunity/impact", headers=_headers(login.json())
    )
    assert resp.status_code == 403