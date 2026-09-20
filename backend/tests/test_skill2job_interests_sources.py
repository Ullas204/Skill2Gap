"""Enhancement tests: candidate interests intake + learning resource sources.

Covers:
- interests persistence through the existing candidate profile
- interests are informational only: they never change match scores/ranks
- interest-match is surfaced as a text reason, not a score component
- NPTEL / Skill India verified sources are present in the training plan
- no fabricated resource URLs and no "verified" status on unverified hosts
"""

from urllib.parse import urlparse

import pytest
from httpx import AsyncClient

from app.skill2job.training.agent import (
    ALLOWED_RESOURCE_HOSTS,
    VERIFIED_RESOURCE_HOSTS,
    _resources_for,
)


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Interests Candidate", "email": email, "password": password},
    )
    assert resp.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


RESUME_TEXT = b"""Sana Khan
Mumbai, India | sana.khan@example.com

SKILLS
Python, Git, PostgreSQL

EXPERIENCE
Software Developer | DataWorks | Mumbai
Jan 2022 - Present
Built Python services and database tooling.

EDUCATION
B.E. Computer Science, VJTI, 2017 - 2021
"""


# ─── Phase 1: interests persistence ──────────────────────────────────────


@pytest.mark.asyncio
async def test_interests_persist_and_return(client: AsyncClient):
    tokens = await _register_and_login(client, "interests@test.com")
    headers = _headers(tokens)

    empty = await client.get("/api/v1/skill2job/profile/interests", headers=headers)
    assert empty.status_code == 200
    assert empty.json()["interests"] == []

    saved = await client.put(
        "/api/v1/skill2job/profile/interests",
        json={"interests": ["AI/ML", "Data Science", "AI/ML", "  "]},
        headers=headers,
    )
    assert saved.status_code == 200
    assert saved.json()["interests"] == ["AI/ML", "Data Science"]

    fetched = await client.get("/api/v1/skill2job/profile/interests", headers=headers)
    assert fetched.json()["interests"] == ["AI/ML", "Data Science"]

    profile = await client.get("/api/v1/skill2job/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["profile"]["interests"] == ["AI/ML", "Data Science"]

    updated = await client.put(
        "/api/v1/skill2job/profile/interests",
        json={"interests": ["Web Development"]},
        headers=headers,
    )
    assert updated.json()["interests"] == ["Web Development"]


@pytest.mark.asyncio
async def test_interests_endpoint_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Interests", "rec_interests@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    resp = await client.get(
        "/api/v1/skill2job/profile/interests", headers=_headers(login.json())
    )
    assert resp.status_code == 403


# ─── Phase 1: interests do not affect scoring ────────────────────────────


@pytest.mark.asyncio
async def test_interests_never_change_match_scores(client: AsyncClient):
    tokens = await _register_and_login(client, "fairness@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )

    baseline = await client.post("/api/v1/skill2job/jobs/match", json={}, headers=headers)
    assert baseline.status_code == 200
    scores_before = {m["job_id"]: m["overall_score"] for m in baseline.json()}
    assert scores_before

    await client.put(
        "/api/v1/skill2job/profile/interests",
        json={"interests": ["AI/ML", "Data Science", "Web Development", "Cloud & DevOps"]},
        headers=headers,
    )
    richer = await client.post("/api/v1/skill2job/jobs/match", json={}, headers=headers)
    scores_after = {m["job_id"]: m["overall_score"] for m in richer.json()}

    # Interests are informational only: every score must be bit-identical.
    assert scores_after == scores_before
    for m in richer.json():
        assert isinstance(m["reasons"], list) and m["reasons"]
        assert 0 <= m["overall_score"] <= 100


@pytest.mark.asyncio
async def test_interest_match_shown_as_reason_text(client: AsyncClient):
    tokens = await _register_and_login(client, "reasons@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )
    await client.put(
        "/api/v1/skill2job/profile/interests",
        json={"interests": ["AI/ML", "Data Science", "Web Development"]},
        headers=headers,
    )
    matches = (await client.post("/api/v1/skill2job/jobs/match", json={}, headers=headers)).json()
    shown = [r for m in matches for r in m["reasons"]]
    assert any(r.startswith("Interest match") for r in shown)


# ─── Phase 2: resource sources, verified status, no fabrication ──────────


@pytest.mark.asyncio
async def test_training_plan_has_verified_nptel_and_skill_india(client: AsyncClient):
    tokens = await _register_and_login(client, "sources@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )
    plan = (await client.get("/api/v1/skill2job/training/plan", headers=headers)).json()
    assert plan["total_modules"] > 0

    modules = {m["provider"]: m for m in plan["modules"] if m["provider"] in ("NPTEL", "Skill India")}
    assert modules["NPTEL"]["url"] == "https://nptel.ac.in/courses"
    assert modules["NPTEL"]["source_status"] == "verified"
    assert modules["NPTEL"]["resource_type"] == "course_catalog"
    assert modules["Skill India"]["url"] == "https://www.skillindiadigital.gov.in/"
    assert modules["Skill India"]["source_status"] == "verified"

    # Verified modules may only point at trusted hosts.
    for module in plan["modules"]:
        if module["source_status"] == "verified":
            assert module["url"] and urlparse(module["url"]).netloc in VERIFIED_RESOURCE_HOSTS


@pytest.mark.asyncio
async def test_no_fabricated_resource_urls(client: AsyncClient):
    tokens = await _register_and_login(client, "no_fake@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )
    plan = (await client.get("/api/v1/skill2job/training/plan", headers=headers)).json()

    for module in plan["modules"]:
        if module["url"]:
            parsed = urlparse(module["url"])
            assert parsed.scheme == "https"
            assert parsed.netloc, "URL must have a host"
            assert parsed.netloc in ALLOWED_RESOURCE_HOSTS
        assert module["source_status"] in ("verified", "unverified")
        assert "example" not in module["url"].lower()
        assert "todo" not in module["url"].lower()
        assert not module["provider"].lower().startswith("provider")


@pytest.mark.asyncio
async def test_unknown_skill_fallback_returns_verified_catalogs_only():
    resources = _resources_for("quantum-computing-xyz")
    providers = {r["provider"] for r in resources}
    assert providers == {"NPTEL", "Skill India"}
    assert all(r["type"] == "course_catalog" for r in resources)
    assert all(r["verified"] is True for r in resources)
    for r in resources:
        assert urlparse(r["url"]).netloc in VERIFIED_RESOURCE_HOSTS