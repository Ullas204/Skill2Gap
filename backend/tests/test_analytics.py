"""Phase 9 — Enterprise Workforce Analytics & BI Platform Tests."""

import pytest
from httpx import AsyncClient

from app.core.security import hash_password
from app.repositories.user import UserRepository
from app.services.auth import AuthService


# ─── Helpers ─────────────────────────────────────────────────────────


async def _create_user_and_login(client: AsyncClient, user_repo: UserRepository, email: str, role: str = "candidate") -> str:
    """Create a user with the given role directly in DB (public registration is candidate-only)."""
    password = "SecureP@ss123"
    user = await user_repo.create(
        full_name=f"Test {role.title()}",
        email=email,
        password_hash=hash_password(password),
        is_active=True,
        is_verified=True,
    )
    role_obj = await user_repo.find_role_by_name(role)
    await user_repo.assign_role(user.id, role_obj.id)
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


async def _create_admin_and_login(client: AsyncClient, user_repo: UserRepository, email: str) -> str:
    password = "SecureP@ss123"
    user = await user_repo.create(
        full_name="Test Admin",
        email=email,
        password_hash=hash_password(password),
        is_active=True,
        is_verified=True,
    )
    admin_role = await user_repo.find_role_by_name("admin")
    await user_repo.assign_role(user.id, admin_role.id)
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def candidate_token(client: AsyncClient, user_repo: UserRepository) -> str:
    return await _create_user_and_login(client, user_repo, "analytics_cand@test.com", "candidate")


@pytest.fixture
async def recruiter_token(client: AsyncClient, user_repo: UserRepository) -> str:
    return await _create_user_and_login(client, user_repo, "analytics_rec@test.com", "recruiter")


@pytest.fixture
async def hr_token(client: AsyncClient, user_repo: UserRepository) -> str:
    return await _create_user_and_login(client, user_repo, "analytics_hr@test.com", "hr")


@pytest.fixture
async def admin_token(client: AsyncClient, user_repo: UserRepository) -> str:
    return await _create_admin_and_login(client, user_repo, "analytics_admin@test.com")


# ─── Candidate Analytics ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_candidate_analytics_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/candidate", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_candidate_analytics_returns_200(client: AsyncClient, candidate_token: str):
    resp = await client.get("/api/v1/analytics/candidate", headers=_auth(candidate_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "skill_match_pct" in data
    assert "applications_by_status" in data
    assert isinstance(data["strongest_skills"], list)
    assert isinstance(data["score_trend"], dict)


# ─── Recruiter Analytics ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_recruiter_analytics_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/recruiter", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_recruiter_analytics_returns_200(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/api/v1/analytics/recruiter", headers=_auth(recruiter_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "total_jobs" in data
    assert "active_jobs" in data
    assert "hire_rate" in data
    assert isinstance(data["pipeline_velocity"], list)


@pytest.mark.asyncio
async def test_recruiter_analytics_denied_for_candidate(client: AsyncClient, candidate_token: str):
    resp = await client.get("/api/v1/analytics/recruiter", headers=_auth(candidate_token))
    assert resp.status_code == 403


# ─── HR Analytics ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_hr_analytics_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/hr", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_hr_analytics_returns_200(client: AsyncClient, hr_token: str):
    resp = await client.get("/api/v1/analytics/hr", headers=_auth(hr_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "total_headcount" in data
    assert "diversity_index" in data
    assert isinstance(data["hiring_funnel"], list)


@pytest.mark.asyncio
async def test_hr_analytics_denied_for_recruiter(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/api/v1/analytics/hr", headers=_auth(recruiter_token))
    assert resp.status_code == 403


# ─── Admin Analytics ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_admin_analytics_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/admin", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_analytics_returns_200(client: AsyncClient, admin_token: str):
    resp = await client.get("/api/v1/analytics/admin", headers=_auth(admin_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "total_users" in data
    assert "active_users" in data
    assert "total_jobs" in data
    assert "total_applications" in data
    assert "system_health_score" in data
    assert "storage_used_mb" in data
    assert "api_calls_today" in data
    assert isinstance(data["users_by_role"], list)
    assert isinstance(data["users_trend"], dict)
    assert isinstance(data["security_events"], list)
    assert isinstance(data["system_load"], list)


@pytest.mark.asyncio
async def test_admin_analytics_denied_for_candidate(client: AsyncClient, candidate_token: str):
    resp = await client.get("/api/v1/analytics/admin", headers=_auth(candidate_token))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_analytics_denied_for_recruiter(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/api/v1/analytics/admin", headers=_auth(recruiter_token))
    assert resp.status_code == 403


# ─── Executive KPIs ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_executive_kpis_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/executive", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_executive_kpis_returns_200_for_hr(client: AsyncClient, hr_token: str):
    resp = await client.get("/api/v1/analytics/executive", headers=_auth(hr_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "revenue_per_hire" in data
    assert "cost_per_hire" in data
    assert isinstance(data["quarterly_trends"], dict)


@pytest.mark.asyncio
async def test_executive_kpis_denied_for_candidate(client: AsyncClient, candidate_token: str):
    resp = await client.get("/api/v1/analytics/executive", headers=_auth(candidate_token))
    assert resp.status_code == 403


# ─── Predictions ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_predictions_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/predictions", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_predictions_returns_200(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/api/v1/analytics/predictions", headers=_auth(recruiter_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "demand_forecast" in data
    assert "confidence_score" in data
    assert isinstance(data["recommendations"], list)


@pytest.mark.asyncio
async def test_predictions_denied_for_candidate(client: AsyncClient, candidate_token: str):
    resp = await client.get("/api/v1/analytics/predictions", headers=_auth(candidate_token))
    assert resp.status_code == 403


# ─── AI Insights ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_insights_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/insights", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_insights_returns_200(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/api/v1/analytics/insights", headers=_auth(recruiter_token))
    assert resp.status_code == 200
    data = resp.json()
    assert "insights" in data
    assert "total" in data
    assert isinstance(data["categories"], list)


@pytest.mark.asyncio
async def test_insights_denied_for_candidate(client: AsyncClient, candidate_token: str):
    resp = await client.get("/api/v1/analytics/insights", headers=_auth(candidate_token))
    assert resp.status_code == 403


# ─── Reports CRUD ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_reports_requires_auth(client: AsyncClient):
    resp = await client.get("/api/v1/analytics/reports", headers={"Authorization": "Bearer invalid"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_list_reports_returns_empty(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/api/v1/analytics/reports", headers=_auth(recruiter_token))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 0
    assert isinstance(data["reports"], list)


@pytest.mark.asyncio
async def test_create_report(client: AsyncClient, recruiter_token: str):
    resp = await client.post(
        "/api/v1/analytics/reports",
        headers=_auth(recruiter_token),
        json={"title": "Test Report", "report_type": "recruiter"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Report"
    assert data["report_type"] == "recruiter"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_report_denied_for_candidate(client: AsyncClient, candidate_token: str):
    resp = await client.post(
        "/api/v1/analytics/reports",
        headers=_auth(candidate_token),
        json={"title": "Unauthorized Report", "report_type": "candidate"},
    )
    assert resp.status_code == 403


# ─── Export ──────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_export_report(client: AsyncClient, recruiter_token: str):
    resp = await client.post(
        "/api/v1/analytics/export",
        headers=_auth(recruiter_token),
        json={"report_type": "recruiter", "format": "pdf"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "download_url" in data
    assert data["format"] == "pdf"


@pytest.mark.asyncio
async def test_export_report_denied_for_candidate(client: AsyncClient, candidate_token: str):
    resp = await client.post(
        "/api/v1/analytics/export",
        headers=_auth(candidate_token),
        json={"report_type": "recruiter", "format": "csv"},
    )
    assert resp.status_code == 403


# ─── Alert Rules ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_alerts(client: AsyncClient, recruiter_token: str):
    resp = await client.get("/api/v1/analytics/alerts", headers=_auth(recruiter_token))
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_create_alert_rule(client: AsyncClient, recruiter_token: str):
    resp = await client.post(
        "/api/v1/analytics/alerts",
        headers=_auth(recruiter_token),
        json={
            "alert_type": "hiring_delay",
            "title": "Test Alert",
            "condition_config": {"metric": "time_to_fill", "operator": "gt", "value": 30},
            "threshold": 30,
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["title"] == "Test Alert"
    assert data["alert_type"] == "hiring_delay"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_alert_denied_for_candidate(client: AsyncClient, candidate_token: str):
    resp = await client.post(
        "/api/v1/analytics/alerts",
        headers=_auth(candidate_token),
        json={
            "alert_type": "system_health",
            "title": "Test",
            "condition_config": {},
        },
    )
    assert resp.status_code == 403


# ─── Dashboard Layout ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_dashboard_layout_empty(client: AsyncClient, recruiter_token: str):
    resp = await client.get(
        "/api/v1/analytics/dashboard-layout",
        headers=_auth(recruiter_token),
        params={"dashboard_key": "recruiter_main"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_save_and_get_dashboard_layout(client: AsyncClient, recruiter_token: str):
    resp = await client.post(
        "/api/v1/analytics/dashboard-layout",
        headers=_auth(recruiter_token),
        json={
            "dashboard_key": "recruiter_main",
            "layout_config": {"widgets": ["kpi", "chart", "table"]},
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["dashboard_key"] == "recruiter_main"

    resp2 = await client.get(
        "/api/v1/analytics/dashboard-layout",
        headers=_auth(recruiter_token),
        params={"dashboard_key": "recruiter_main"},
    )
    assert resp2.status_code == 200
    assert resp2.json()["layout_config"]["widgets"] == ["kpi", "chart", "table"]


@pytest.mark.asyncio
async def test_dashboard_layout_upsert(client: AsyncClient, recruiter_token: str):
    for layout in [{"widgets": ["a"]}, {"widgets": ["a", "b"]}]:
        await client.post(
            "/api/v1/analytics/dashboard-layout",
            headers=_auth(recruiter_token),
            json={"dashboard_key": "test_upsert", "layout_config": layout},
        )
    resp = await client.get(
        "/api/v1/analytics/dashboard-layout",
        headers=_auth(recruiter_token),
        params={"dashboard_key": "test_upsert"},
    )
    assert resp.json()["layout_config"]["widgets"] == ["a", "b"]


@pytest.mark.asyncio
async def test_dashboard_layout_denied_for_candidate(client: AsyncClient, candidate_token: str):
    resp = await client.post(
        "/api/v1/analytics/dashboard-layout",
        headers=_auth(candidate_token),
        json={"dashboard_key": "test", "layout_config": {}},
    )
    assert resp.status_code == 403
