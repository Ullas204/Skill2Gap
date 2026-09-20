"""Phase 7 Skill2Job Opportunity Unlock tests.

Covers:
- what-if simulation improves scores with ONLY candidate-proposed skills
- persisted simulation history
- dashboard aggregates potential / unlocked / top roles
- candidate-only authorization
"""

import pytest
from httpx import AsyncClient


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Unlock Candidate", "email": email, "password": password},
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
async def test_simulation_with_prospective_skills(client: AsyncClient):
    tokens = await _register_and_login(client, "sim_run@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )

    resp = await client.post(
        "/api/v1/skill2job/opportunity/simulate",
        json={
            "dream_job_title": "Data Scientist",
            "skills_to_add": ["PyTorch", "scikit-learn", "Airflow"],
        },
        headers=headers,
    )
    assert resp.status_code == 200
    sim = resp.json()
    assert sim["simulation_version"].startswith("skill2job-simulation")
    assert {s.lower() for s in sim["skills_added"]} == {"pytorch", "scikit-learn", "airflow"}
    assert sim["baseline"] and sim["simulated"]
    assert sim["baseline"][0]["overall_score"] <= sim["simulated"][0]["overall_score"]
    # only skills the candidate proposed can appear as newly matched
    proposed = {"pytorch", "scikit-learn", "airflow"}
    for detail in sim["top_uplift"]:
        for skill in detail["newly_matched_skills"]:
            assert skill.lower() in proposed
    assert 0 <= sim["unlocked_count"] <= len(sim["simulated"])
    assert isinstance(sim["notes"], list) and sim["notes"]


@pytest.mark.asyncio
async def test_simulation_without_skills_is_honest(client: AsyncClient):
    tokens = await _register_and_login(client, "sim_empty@test.com")
    headers = _headers(tokens)
    resp = await client.post(
        "/api/v1/skill2job/opportunity/simulate",
        json={"dream_job_title": "Data Engineer"},
        headers=headers,
    )
    assert resp.status_code == 200
    sim = resp.json()
    assert sim["skills_added"] == []
    assert sim["unlocked_count"] == 0
    assert any(
        "Add prospective skills" in note for note in sim["notes"]
    )


@pytest.mark.asyncio
async def test_simulation_history_and_dashboard(client: AsyncClient):
    tokens = await _register_and_login(client, "sim_history@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/opportunity/simulate",
        json={"dream_job_title": "Backend Engineer", "skills_to_add": ["FastAPI", "Redis"]},
        headers=headers,
    )

    history = await client.get(
        "/api/v1/skill2job/opportunity/simulations", headers=headers
    )
    assert history.status_code == 200
    hist = history.json()
    assert hist["total"] == 1
    assert hist["items"][0]["dream_job_title"] == "Backend Engineer"

    dash = await client.get(
        "/api/v1/skill2job/opportunity/dashboard", headers=headers
    )
    assert dash.status_code == 200
    body = dash.json()
    assert body["potential"] >= 0
    assert body["unlocked_count"] >= 0
    assert isinstance(body["top_roles"], list)


@pytest.mark.asyncio
async def test_opportunity_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Sim", "rec_sim@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    resp = await client.post(
        "/api/v1/skill2job/opportunity/simulate",
        json={"dream_job_title": "Engineer", "skills_to_add": ["FastAPI"]},
        headers=_headers(login.json()),
    )
    assert resp.status_code == 403