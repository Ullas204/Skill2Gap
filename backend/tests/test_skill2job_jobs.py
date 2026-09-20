"""Phase 4 Skill2Job Local Job Intelligence tests.

Covers:
- curated catalog auto-seed (40 roles) with pagination
- location / remote-only / keyword filters
- candidate-aware job fetch (no fabricated results, catalog-only)
- catalog counts for the dashboard
- seed endpoint authorization (super_admin only)
"""

import pytest
from httpx import AsyncClient


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Jobs Candidate", "email": email, "password": password},
    )
    assert resp.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


@pytest.mark.asyncio
async def test_catalog_autoseeds_and_is_paginated(client: AsyncClient):
    tokens = await _register_and_login(client, "catalog@test.com")
    headers = _headers(tokens)

    resp = await client.get("/api/v1/skill2job/jobs/catalog", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 40
    assert len(body["jobs"]) == 20

    titles = {j["title"] for j in body["jobs"]}
    assert "Backend Engineer (Python/FastAPI)" in titles
    first = body["jobs"][0]
    for key in ("required_skills", "preferred_skills", "salary_range", "remote_type", "source"):
        assert key in first

    page2 = await client.get(
        "/api/v1/skill2job/jobs/catalog", params={"offset": 20}, headers=headers
    )
    body2 = page2.json()
    assert body2["total"] == 40 and len(body2["jobs"]) == 20
    assert body2["jobs"][0]["external_id"] != body["jobs"][0]["external_id"]


@pytest.mark.asyncio
async def test_catalog_location_and_remote_filters(client: AsyncClient):
    tokens = await _register_and_login(client, "catalog_filters@test.com")
    headers = _headers(tokens)

    bengaluru = await client.get(
        "/api/v1/skill2job/jobs/catalog", params={"location": "Bengaluru"}, headers=headers
    )
    body = bengaluru.json()
    assert body["total"] > 0
    assert all(j["location"] == "Bengaluru" for j in body["jobs"])

    remote = await client.get(
        "/api/v1/skill2job/jobs/catalog", params={"remote_only": "true"}, headers=headers
    )
    body_r = remote.json()
    assert body_r["total"] > 0
    assert all(j["remote_type"] in ("remote", "hybrid") for j in body_r["jobs"])

    kw = await client.get(
        "/api/v1/skill2job/jobs/catalog", params={"keyword": "kafka"}, headers=headers
    )
    body_k = kw.json()
    assert body_k["total"] >= 1
    assert all(
        "kafka" in (j["title"] + j["description"] + j["company"]).lower()
        for j in body_k["jobs"]
    )


@pytest.mark.asyncio
async def test_catalog_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Jobs", "rec_jobs@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    resp = await client.get(
        "/api/v1/skill2job/jobs/catalog", headers=_headers(login.json())
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_matched_jobs_are_candidate_aware(client: AsyncClient):
    tokens = await _register_and_login(client, "matched@test.com")
    headers = _headers(tokens)

    await client.put(
        "/api/v1/candidates/profile",
        json={"current_role": "Data Engineer", "location": "Bengaluru"},
        headers=headers,
    )

    resp = await client.get(
        "/api/v1/skill2job/jobs/matched",
        params={"location": "Bengaluru"},
        headers=headers,
    )
    assert resp.status_code == 200
    jobs = resp.json()
    assert len(jobs) <= 10
    assert jobs, "expected at least one catalog job for a data engineer in Bengaluru"
    titles = [j["title"].lower() for j in jobs[:3]]
    assert any(
        term in title for term in ("data", "backend", "engineer") for title in titles
    )
    assert all(
        j["remote_type"] == "remote" or j["location"] == "Bengaluru"
        for j in jobs[:3]
    )


@pytest.mark.asyncio
async def test_job_counts_for_dashboard(client: AsyncClient):
    tokens = await _register_and_login(client, "counts@test.com")
    headers = _headers(tokens)

    resp = await client.get("/api/v1/skill2job/jobs/counts", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 40
    assert body["remote"] > 0
    assert len(body["top_locations"]) >= 1
    total_by_location = sum(item["count"] for item in body["top_locations"])
    assert total_by_location <= 40


@pytest.mark.asyncio
async def test_seed_requires_super_admin(client: AsyncClient, _create_user_with_role):
    tokens = await _register_and_login(client, "seed_plain@test.com")
    resp = await client.post(
        "/api/v1/skill2job/jobs/seed", headers=_headers(tokens)
    )
    assert resp.status_code == 403

    user, password = await _create_user_with_role(
        "Admin Jobs", "admin_jobs@test.com", "SecureP@ss123", "super_admin"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    first = (await client.post(
        "/api/v1/skill2job/jobs/seed", headers=_headers(login.json())
    )).json()
    assert first["total"] == 40
    assert first["loaded"] == 40  # first seed populates the catalog

    second = (await client.post(
        "/api/v1/skill2job/jobs/seed", headers=_headers(login.json())
    )).json()
    assert second["total"] == 40
    assert second["loaded"] == 0  # idempotent re-seed


@pytest.mark.asyncio
async def test_seed_is_idempotent_across_calls(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Admin Jobs 2", "admin_jobs2@test.com", "SecureP@ss123", "super_admin"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    headers = _headers(login.json())
    first = (await client.post("/api/v1/skill2job/jobs/seed", headers=headers)).json()
    second = (await client.post("/api/v1/skill2job/jobs/seed", headers=headers)).json()
    assert first["total"] == second["total"] == 40
    assert second["loaded"] == 0