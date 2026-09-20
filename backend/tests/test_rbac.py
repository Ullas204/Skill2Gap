import pytest
from httpx import AsyncClient

from app.core.security import decode_token, hash_password, verify_password
from app.domain.models import Role, User
from app.repositories.user import UserRepository
from app.services.auth import AuthService


# ─── Registration with Role Selection ────────────────────────────────


@pytest.mark.asyncio
async def test_register_candidate_default(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Test Candidate", "email": "test_cand@example.com", "password": "SecureP@ss123"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test_cand@example.com"
    assert "candidate" in data["roles"]


@pytest.mark.asyncio
async def test_register_with_recruiter_role_ignored(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Test Recruiter", "email": "test_rec_rbac@example.com", "password": "SecureP@ss123", "role": "recruiter"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "candidate" in data["roles"]


@pytest.mark.asyncio
async def test_register_with_hr_role_ignored(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Test HR", "email": "test_hr_rbac@example.com", "password": "SecureP@ss123", "role": "hr"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "candidate" in data["roles"]


@pytest.mark.asyncio
async def test_register_admin_role_ignored(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Fake Admin", "email": "fake_admin_rbac@example.com", "password": "SecureP@ss123", "role": "admin"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "candidate" in data["roles"]


@pytest.mark.asyncio
async def test_register_invalid_role_ignored(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Bad Role", "email": "bad_rbac@example.com", "password": "SecureP@ss123", "role": "superadmin"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "candidate" in data["roles"]


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient, auth_service: AuthService) -> None:
    await auth_service.register("Dupe User", "dupe_role@example.com", "SecureP@ss123")
    response = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Dupe User", "email": "dupe_role@example.com", "password": "SecureP@ss123"},
    )
    assert response.status_code == 409


# ─── JWT Role Claims ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_login_jwt_contains_roles(client: AsyncClient, auth_service: AuthService) -> None:
    await auth_service.register("JWT Test", "jwt@example.com", "SecureP@ss123")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "jwt@example.com", "password": "SecureP@ss123"},
    )
    assert response.status_code == 200
    data = response.json()
    payload = decode_token(data["access_token"])
    assert "roles" in payload
    assert "candidate" in payload["roles"]
    assert payload["type"] == "access"


@pytest.mark.asyncio
async def test_login_recruiter_jwt_contains_recruiter_role(client: AsyncClient, _create_user_with_role) -> None:
    await _create_user_with_role("Rec JWT", "rec_jwt_rbac@example.com", "SecureP@ss123", "recruiter")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "rec_jwt_rbac@example.com", "password": "SecureP@ss123"},
    )
    assert response.status_code == 200
    payload = decode_token(response.json()["access_token"])
    assert "recruiter" in payload["roles"]


# ─── Token Refresh ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_refresh_token_returns_new_tokens(client: AsyncClient, auth_service: AuthService) -> None:
    await auth_service.register("Refresh Test", "refresh@example.com", "SecureP@ss123")
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "SecureP@ss123"},
    )
    refresh_token = login_resp.json()["refresh_token"]
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid.token.here"},
    )
    assert response.status_code == 401


# ─── Auth: /me endpoint ─────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_me_returns_roles(client: AsyncClient, auth_service: AuthService) -> None:
    user = await auth_service.register("Me Test", "me@example.com", "SecureP@ss123")
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "SecureP@ss123"},
    )
    token = login_resp.json()["access_token"]
    response = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "me@example.com"
    assert "candidate" in data["roles"]


# ─── Roles API ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_roles(client: AsyncClient) -> None:
    response = await client.get("/api/v1/auth/roles")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    names = {r["name"] for r in data}
    assert "admin" in names
    assert "candidate" in names
    assert "recruiter" in names
    assert "hr" in names


# ─── Dashboard API: Authentication ──────────────────────────────────


@pytest.mark.asyncio
async def test_candidate_dashboard_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/dashboard/candidate")
    assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_recruiter_dashboard_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/dashboard/recruiter")
    assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_hr_dashboard_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/dashboard/hr")
    assert response.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_admin_dashboard_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/dashboard/admin")
    assert response.status_code in (401, 403, 422)


# ─── Dashboard API: Role-Based Access ───────────────────────────────


async def _login(client: AsyncClient, email: str, password: str) -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_candidate_can_access_candidate_dashboard(client: AsyncClient, auth_service: AuthService) -> None:
    await auth_service.register("Cand Dash", "cand_dash@example.com", "SecureP@ss123")
    token = await _login(client, "cand_dash@example.com", "SecureP@ss123")
    response = await client.get("/api/v1/dashboard/candidate", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "total_applications" in response.json()


@pytest.mark.asyncio
async def test_candidate_cannot_access_admin_dashboard(client: AsyncClient, auth_service: AuthService) -> None:
    await auth_service.register("Cand NoAdmin", "cand_noadmin@example.com", "SecureP@ss123")
    token = await _login(client, "cand_noadmin@example.com", "SecureP@ss123")
    response = await client.get("/api/v1/dashboard/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_recruiter_can_access_recruiter_dashboard(client: AsyncClient, _create_user_with_role) -> None:
    await _create_user_with_role("Rec Dash", "rec_dash@example.com", "SecureP@ss123", "recruiter")
    token = await _login(client, "rec_dash@example.com", "SecureP@ss123")
    response = await client.get("/api/v1/dashboard/recruiter", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "total_jobs" in response.json()


@pytest.mark.asyncio
async def test_recruiter_cannot_access_admin_dashboard(client: AsyncClient, _create_user_with_role) -> None:
    await _create_user_with_role("Rec NoAdmin", "rec_noadmin@example.com", "SecureP@ss123", "recruiter")
    token = await _login(client, "rec_noadmin@example.com", "SecureP@ss123")
    response = await client.get("/api/v1/dashboard/admin", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_hr_can_access_hr_dashboard(client: AsyncClient, _create_user_with_role) -> None:
    await _create_user_with_role("HR Dash", "hr_dash@example.com", "SecureP@ss123", "hr")
    token = await _login(client, "hr_dash@example.com", "SecureP@ss123")
    response = await client.get("/api/v1/dashboard/hr", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert "open_positions" in response.json()


@pytest.mark.asyncio
async def test_hr_can_access_recruiter_dashboard(client: AsyncClient, _create_user_with_role) -> None:
    await _create_user_with_role("HR Rec", "hr_rec@example.com", "SecureP@ss123", "hr")
    token = await _login(client, "hr_rec@example.com", "SecureP@ss123")
    response = await client.get("/api/v1/dashboard/recruiter", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_candidate_cannot_access_recruiter_dashboard(client: AsyncClient, auth_service: AuthService) -> None:
    await auth_service.register("Cand NoRec", "cand_norec@example.com", "SecureP@ss123")
    token = await _login(client, "cand_norec@example.com", "SecureP@ss123")
    response = await client.get("/api/v1/dashboard/recruiter", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


# ─── Admin API: Role-Based Access ───────────────────────────────────


@pytest.mark.asyncio
async def test_non_admin_cannot_list_users(client: AsyncClient, _create_user_with_role) -> None:
    await _create_user_with_role("Non Admin", "non_admin@example.com", "SecureP@ss123", "recruiter")
    token = await _login(client, "non_admin@example.com", "SecureP@ss123")
    response = await client.get("/api/v1/dashboard/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_non_admin_cannot_view_audit_logs(client: AsyncClient, auth_service: AuthService) -> None:
    await auth_service.register("No Audit", "no_audit@example.com", "SecureP@ss123")
    token = await _login(client, "no_audit@example.com", "SecureP@ss123")
    response = await client.get("/api/v1/dashboard/admin/audit-logs", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


# ─── Password Security ─────────────────────────────────────────────


def test_password_hashing() -> None:
    password = "SecureP@ss123"
    hashed = hash_password(password)
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("WrongPassword", hashed)


# ─── Login: Invalid Credentials ─────────────────────────────────────


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, auth_service: AuthService) -> None:
    await auth_service.register("Login Fail", "login_fail@example.com", "SecureP@ss123")
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "login_fail@example.com", "password": "WrongPassword"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nonexistent@example.com", "password": "SecureP@ss123"},
    )
    assert response.status_code == 401


# ─── Logout ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, auth_service: AuthService) -> None:
    await auth_service.register("Logout Test", "logout@example.com", "SecureP@ss123")
    token = await _login(client, "logout@example.com", "SecureP@ss123")
    response = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_logout_requires_auth(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/logout")
    assert response.status_code in (401, 403, 422)


# ─── Registration Validation ────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_validation_error(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "", "email": "not-an-email", "password": "short"},
    )
    assert response.status_code == 422
