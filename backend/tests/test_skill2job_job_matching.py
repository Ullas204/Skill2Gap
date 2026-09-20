"""Phase 5 Skill2Job Job Matching Agent tests.

Covers:
- deterministic ranking from the existing MatchingEngine (no fabricated results)
- persisted matches with auditable score components
- suggested skills are grounded (missing required skills / transferable)
- retrieval endpoint returns the stored matches sorted by score
- candidate-only authorization
"""

import pytest
from httpx import AsyncClient


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Match Candidate", "email": email, "password": password},
    )
    assert resp.status_code == 201
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return login.json()


SECTIONED_RESUME = b"""Amit Verma
Bengaluru, India | amit.verma@example.com

SUMMARY
Backend Python developer with 4 years of experience building web services.

SKILLS
Python, Django, SQL, Docker, Redis

EXPERIENCE
Backend Developer | WebScale | Bengaluru
Jan 2022 - Present
Built Django REST services and optimized SQL queries.

EDUCATION
B.Tech Computer Science, IIT Bombay, 2016 - 2020
"""


async def _prime_candidate(client: AsyncClient, headers: dict, email: str) -> None:
    await client.put(
        "/api/v1/candidates/profile",
        json={"current_role": "Backend Engineer", "location": "Bengaluru"},
        headers=headers,
    )
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", SECTIONED_RESUME, "text/plain")},
        headers=headers,
    )


@pytest.mark.asyncio
async def test_match_ranks_and_persists(client: AsyncClient):
    tokens = await _register_and_login(client, "match_run@test.com")
    headers = _headers(tokens)
    await _prime_candidate(client, headers, "match_run@test.com")

    resp = await client.post("/api/v1/skill2job/jobs/match", json={}, headers=headers)
    assert resp.status_code == 200
    matches = resp.json()
    assert len(matches) == 10  # default limit
    scores = [m["overall_score"] for m in scores_from(matches)]
    assert scores == sorted(scores, reverse=True)

    top = matches[0]
    assert top["title"]
    assert top["company"]
    assert 0 <= top["overall_score"] <= 100
    assert top["strength_level"] in ("excellent", "good", "average", "low")
    assert top["recommendation"] in ("strongly_recommend", "recommend", "consider", "not_recommended")
    # grounded suggestions only
    for skill in top["suggested_skills"]:
        assert skill not in {"python", "django", "sql"}


@pytest.mark.asyncio
async def test_match_scores_are_deterministic_and_repeatable(client: AsyncClient):
    tokens = await _register_and_login(client, "match_det@test.com")
    headers = _headers(tokens)
    await _prime_candidate(client, headers, "match_det@test.com")

    first = (await client.post("/api/v1/skill2job/jobs/match", json={}, headers=headers)).json()
    second = (await client.post("/api/v1/skill2job/jobs/match", json={}, headers=headers)).json()
    assert [m["job_id"] for m in first] == [m["job_id"] for m in second]
    assert [m["overall_score"] for m in first] == [m["overall_score"] for m in second]

    stored = await client.get("/api/v1/skill2job/jobs/match", headers=headers)
    assert stored.status_code == 200
    stored_body = stored.json()
    assert stored_body and stored_body[0]["job_id"] == first[0]["job_id"]


@pytest.mark.asyncio
async def test_match_honors_job_subset(client: AsyncClient):
    tokens = await _register_and_login(client, "match_subset@test.com")
    headers = _headers(tokens)
    await _prime_candidate(client, headers, "match_subset@test.com")

    catalog = (await client.get(
        "/api/v1/skill2job/jobs/catalog", params={"keyword": "python"}, headers=headers
    )).json()
    job_ids = [j["id"] for j in catalog["jobs"]][:3]
    assert len(job_ids) == 3

    resp = await client.post(
        "/api/v1/skill2job/jobs/match", json={"job_ids": job_ids, "limit": 10}, headers=headers
    )
    assert resp.status_code == 200
    body = resp.json()
    assert {m["job_id"] for m in body} == set(job_ids)


@pytest.mark.asyncio
async def test_match_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Match", "rec_match@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    resp = await client.post(
        "/api/v1/skill2job/jobs/match", json={}, headers=_headers(login.json())
    )
    assert resp.status_code == 403


def scores_from(matches: list[dict]) -> list[dict]:
    return matches