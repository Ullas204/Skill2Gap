"""Phase 3 Skill2Job Candidate Profile Agent tests.

Covers:
- dossier build from existing profile + perception inputs (skills unioned,
  canonicalized, evidence attributed)
- deterministic completeness scoring (platform weights)
- grounded recommendations / suggestions (no fabricated skills)
- cached dossier retrieval
- human-review apply/reject endpoint (only known skills added; no fabrication)
- candidate-only authorization
"""

import pytest
from httpx import AsyncClient


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Profile Candidate", "email": email, "password": password},
    )
    assert resp.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


RESUME_TEXT = b"""Priya Sharma
Bengaluru, India | priya.sharma@example.com

SUMMARY
Data engineer with 3 years of experience building ETL pipelines.

SKILLS
Python, SQL, Airflow, Snowflake, Docker, Git

EXPERIENCE
Data Engineer | DataWorks | Remote
Jan 2023 - Present
Built ETL pipelines with Airflow and Snowflake.

EDUCATION
B.Tech Computer Science, Anna University, 2017 - 2021

LANGUAGES
English, Tamil
"""


@pytest.mark.asyncio
async def test_dossier_build_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Dossier", "dossier_rec@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    resp = await client.post(
        "/api/v1/skill2job/profile/agent/dossier", headers=_headers(login.json())
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_dossier_build_empty_profile(client: AsyncClient):
    tokens = await _register_and_login(client, "dossier_empty@test.com")
    resp = await client.post(
        "/api/v1/skill2job/profile/agent/dossier", headers=_headers(tokens)
    )
    assert resp.status_code == 200
    dossier = resp.json()
    assert dossier["user_id"]
    assert dossier["skill_count"] == 0
    assert dossier["education_count"] == 0
    assert dossier["completeness"]["score"] == 0
    assert "skills" in dossier["completeness"]["missing_sections"]
    assert dossier["recommendations"], "empty profile should yield recommendations"
    categories = {r["category"] for r in dossier["recommendations"]}
    assert "profile_section" in categories
    # no fabricated skills
    assert dossier["suggestions"] == []


@pytest.mark.asyncio
async def test_dossier_unions_and_canonicalizes_skills(client: AsyncClient):
    tokens = await _register_and_login(client, "dossier_union@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )
    await client.put(
        "/api/v1/candidates/profile",
        json={"current_role": "Data Engineer", "location": "Bengaluru"},
        headers=headers,
    )
    resp = await client.post("/api/v1/skill2job/profile/agent/dossier", headers=headers)
    assert resp.status_code == 200
    dossier = resp.json()
    assert dossier["skill_count"] >= 5
    names = {s["name"].lower() for s in dossier["skills"]}
    for expected in ("python", "sql", "airflow", "docker", "git"):
        assert expected in names
    # evidence attribution present
    has_profile_src = any("candidate_profile" in s["sources"] for s in dossier["skills"])
    has_perception_src = any(
        any(src.startswith("perception:") for src in s["sources"]) for s in dossier["skills"]
    )
    assert has_profile_src or has_perception_src
    assert dossier["completeness"]["score"] > 0
    assert dossier["education_count"] == 0  # not auto-created


@pytest.mark.asyncio
async def test_dossier_target_roles_from_perception(client: AsyncClient):
    tokens = await _register_and_login(client, "dossier_roles@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/text",
        data={"text": "Looking for a data engineer role. I know Python and SQL."},
        headers=headers,
    )
    resp = await client.post("/api/v1/skill2job/profile/agent/dossier", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["target_roles"] == ["Data Engineer"]


@pytest.mark.asyncio
async def test_dossier_cached_retrieval(client: AsyncClient):
    tokens = await _register_and_login(client, "dossier_cache@test.com")
    headers = _headers(tokens)
    build = await client.post("/api/v1/skill2job/profile/agent/dossier", headers=headers)
    assert build.status_code == 200
    got = await client.get("/api/v1/skill2job/profile/agent/dossier", headers=headers)
    assert got.status_code == 200
    cached = got.json()
    assert cached["user_id"] == build.json()["user_id"]
    assert cached["version"].startswith("skill2job-profile-")


@pytest.mark.asyncio
async def test_review_applies_only_known_skills(client: AsyncClient, session):
    from app.domain.enums import SkillCategory
    from app.domain.models import Skill

    tokens = await _register_and_login(client, "review_apply@test.com")
    headers = _headers(tokens)
    # create a global skill so the existing ProfileService can resolve it
    session.add(Skill(name="Python", category=SkillCategory.PROGRAMMING_LANGUAGES))
    await session.flush()

    resp = await client.post(
        "/api/v1/skill2job/profile/agent/review",
        json={"skills_to_add": ["Python", "SomeMadeUpSkillXYZ123"], "skills_to_exclude": ["Cobol"], "corrections": []},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    applied = {a["name"].lower() for a in body["applied_skills"] if a.get("applied")}
    skipped = {a["name"].lower() for a in body["applied_skills"] if not a.get("applied")}
    assert "python" in applied
    assert "somemadeupskillxyz123" in skipped
    assert body["excluded_skills"] == ["Cobol"]

    # applying the same skill again reports it as already present (idempotent)
    again = await client.post(
        "/api/v1/skill2job/profile/agent/review",
        json={"skills_to_add": ["Python"], "skills_to_exclude": [], "corrections": []},
        headers=headers,
    )
    reason = {a["name"].lower(): a["reason"] for a in again.json()["applied_skills"]}
    assert reason["python"] == "already on profile"


@pytest.mark.asyncio
async def test_review_applies_safe_profile_field_corrections(client: AsyncClient):
    tokens = await _register_and_login(client, "review_fields@test.com")
    headers = _headers(tokens)
    resp = await client.post(
        "/api/v1/skill2job/profile/agent/review",
        json={
            "skills_to_add": [],
            "skills_to_exclude": [],
            "corrections": [
                {"field": "current_role", "value": "Data Analyst", "note": "human correction"},
                {"field": "unsafe_custom_field", "value": "hack", "note": "should not write"},
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["corrections_applied"][0]["status"] == "applied"
    profile = await client.get("/api/v1/skill2job/profile", headers=headers)
    assert profile.json()["profile"]["current_role"] == "Data Analyst"