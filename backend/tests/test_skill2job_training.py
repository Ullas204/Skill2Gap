"""Phase 8 Skill2Job Training Agent + LangGraph orchestration tests.

Covers:
- grounded learning plan with real provider resources (no hallucinated URLs)
- candidate-confirmed module completion & progress history
- full LangGraph pipeline run with recorded execution trace
- trace retrieval and authorization rules
"""

import pytest
from httpx import AsyncClient


def _headers(tokens: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens['access_token']}"}


async def _register_and_login(client: AsyncClient, email: str, password: str = "SecureP@ss123") -> dict:
    resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Training Candidate", "email": email, "password": password},
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


@pytest.mark.asyncio
async def test_training_plan_is_grounded(client: AsyncClient):
    tokens = await _register_and_login(client, "plan@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )

    resp = await client.get("/api/v1/skill2job/training/plan", headers=headers)
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["version"].startswith("skill2job-training")
    assert plan["total_modules"] > 0
    known_providers = {
        "python.org",
        "Python Institute",
        "PyTorch",
        "scikit-learn",
        "PostgreSQL",
        "Docker",
        "Kubernetes",
        "HashiCorp",
        "FastAPI",
        "React",
        "Django",
        "Apache Airflow",
        "AWS",
        "Apache Kafka",
        "Apache Spark",
        "Scala",
        "Rust",
        "golang.org",
        "Node.js",
        "Linux Foundation",
        "Prometheus",
        "MongoDB",
        "NPTEL",
        "Skill India",
    }
    for module in plan["modules"]:
        assert module["module_key"] and module["skill"]
        if module["url"]:
            assert module["provider"] in known_providers
            assert module["url"].startswith("https://")
        assert module["resource_type"] in ("official_docs", "certification", "course_catalog")
        assert module["source_status"] in ("verified", "unverified")
        if module["url"] is None:
            assert module["source_status"] == "unverified"


@pytest.mark.asyncio
async def test_module_completion_and_progress(client: AsyncClient):
    tokens = await _register_and_login(client, "progress@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )

    plan = (await client.get("/api/v1/skill2job/training/plan", headers=headers)).json()
    module_key = plan["modules"][0]["module_key"]

    unknown = await client.post(
        "/api/v1/skill2job/training/progress",
        json={"module_key": "definitely_not_real", "status": "completed"},
        headers=headers,
    )
    assert unknown.status_code == 200
    assert unknown.json()["ok"] is False

    done = await client.post(
        "/api/v1/skill2job/training/progress",
        json={"module_key": module_key, "status": "completed"},
        headers=headers,
    )
    assert done.status_code == 200
    assert done.json()["ok"] is True

    progress = (await client.get("/api/v1/skill2job/training/progress", headers=headers)).json()
    assert progress["total"] == 1
    item = progress["items"][0]
    assert item["module_key"] == module_key and item["status"] == "completed"
    assert item["completed_at"] is not None


@pytest.mark.asyncio
async def test_langgraph_pipeline_run_records_trace(client: AsyncClient):
    tokens = await _register_and_login(client, "pipeline@test.com")
    headers = _headers(tokens)
    await client.post(
        "/api/v1/skill2job/perception/upload",
        files={"file": ("resume.txt", RESUME_TEXT, "text/plain")},
        headers=headers,
    )

    resp = await client.post("/api/v1/skill2job/training/run", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "completed"
    assert body["run_id"]
    node_names = {s["node"] for s in body["steps"]}
    assert {"gather", "profile", "jobs", "match", "gap", "plan"} <= node_names
    assert body["final"]["plan_count"] > 0

    traces = (await client.get("/api/v1/skill2job/training/traces", headers=headers)).json()
    assert traces["total"] == 1
    assert traces["items"][0]["run_id"] == body["run_id"]

    detail = await client.get(
        f"/api/v1/skill2job/training/traces/{body['run_id']}", headers=headers
    )
    assert detail.status_code == 200
    trace = detail.json()
    assert trace["trace"]["final"]["matched_count"] >= 0


@pytest.mark.asyncio
async def test_training_requires_candidate(client: AsyncClient, _create_user_with_role):
    user, password = await _create_user_with_role(
        "Recruiter Training", "rec_training@test.com", "SecureP@ss123", "recruiter"
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": password}
    )
    resp = await client.get(
        "/api/v1/skill2job/training/plan", headers=_headers(login.json())
    )
    assert resp.status_code == 403