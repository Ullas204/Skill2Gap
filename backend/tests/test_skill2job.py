"""Phase 1 Skill2Job module tests.

Covers:
- module health endpoint (public)
- authentication enforcement (missing / invalid token)
- candidate authorization (recruiter rejected)
- existing candidate profile retrieval
- no fake capability reporting
"""

import pytest
from httpx import AsyncClient


def _candidate_headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Candidate User", "email": email, "password": password},
    )
    assert resp.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


@pytest.mark.asyncio
async def test_health_public_returns_available(client: AsyncClient):
    resp = await client.get("/api/v1/skill2job/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["module"] == "skill2job"
    assert body["status"] == "available"
    assert set(body.keys()) == {"module", "status"}


@pytest.mark.asyncio
async def test_capabilities_requires_authentication(client: AsyncClient):
    # Missing Authorization header is rejected by FastAPI's required-header
    # validation (422) — the platform-wide get_current_user convention. Invalid
    # tokens are rejected with 401 (see test_capabilities_invalid_token_rejected).
    resp = await client.get("/api/v1/skill2job/capabilities")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_capabilities_invalid_token_rejected(client: AsyncClient):
    resp = await client.get(
        "/api/v1/skill2job/capabilities",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_profile_requires_authentication(client: AsyncClient):
    # See note in test_capabilities_requires_authentication.
    resp = await client.get("/api/v1/skill2job/profile")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_profile_invalid_token_rejected(client: AsyncClient):
    resp = await client.get(
        "/api/v1/skill2job/profile",
        headers={"Authorization": "Bearer not-a-valid-token"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_capabilities_candidate_role(client: AsyncClient):
    # Capabilities is an internal implementation-status report gated to admin
    # roles; candidates must never see it.
    tokens = await _register_and_login(client, "s2j_cap@test.com")
    resp = await client.get("/api/v1/skill2job/capabilities", headers=_candidate_headers(tokens))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_capabilities_admin_role(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Skill2Job Admin", "s2j_admin@test.com", "SecureP@ss123", "admin"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    resp = await client.get("/api/v1/skill2job/capabilities", headers=_candidate_headers(login.json()))
    assert resp.status_code == 200
    body = resp.json()
    assert body["module"] == "skill2job"
    assert "profile_connected" in body
    assert isinstance(body["capabilities"], list)
    keys = {c["key"] for c in body["capabilities"]}
    assert "module_foundation" in keys
    assert "authentication_rbac" in keys
    assert "candidate_profile" in keys
    assert "perception" in keys and "training_agent" in keys
    available = {c["key"] for c in body["capabilities"] if c["status"] == "available"}
    assert "perception" in available
    assert "perception_document" in available
    assert "profile_agent" in available
    assert "local_jobs" in available
    assert "job_matching" in available
    assert "skill_gap" in available
    assert "opportunity_unlock" in available
    assert "training_agent" in available
    defer_rules = {c["key"] for c in body["capabilities"] if c["status"] == "deferred"}
    assert "perception" not in defer_rules
    assert defer_rules == set()


@pytest.mark.asyncio
async def test_profile_candidate_returns_existing_profile(client: AsyncClient):
    tokens = await _register_and_login(client, "s2j_prof@test.com")
    resp = await client.get("/api/v1/skill2job/profile", headers=_candidate_headers(tokens))
    assert resp.status_code == 200
    body = resp.json()
    assert body["connected"] is True
    assert "profile" in body and body["profile"]["user_id"] is not None
    assert body["intelligence"] is not None
    assert "skill_summary" in body["intelligence"]


@pytest.mark.asyncio
async def test_capabilities_forbidden_for_recruiter(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter S2J", "s2j_rec@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    tokens = login.json()
    resp = await client.get("/api/v1/skill2job/capabilities", headers=_candidate_headers(tokens))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_profile_forbidden_for_recruiter(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter S2J 2", "s2j_rec2@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": user.email, "password": password},
    )
    tokens = login.json()
    resp = await client.get("/api/v1/skill2job/profile", headers=_candidate_headers(tokens))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_profile_updates_existing_candidate_profile_source(client: AsyncClient):
    tokens = await _register_and_login(client, "s2j_src@test.com")
    headers = _candidate_headers(tokens)
    await client.put(
        "/api/v1/candidates/profile",
        json={"current_role": "Backend Engineer", "location": "Bengaluru"},
        headers=headers,
    )
    resp = await client.get("/api/v1/skill2job/profile", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["profile"]["current_role"] == "Backend Engineer"
    assert body["profile"]["location"] == "Bengaluru"