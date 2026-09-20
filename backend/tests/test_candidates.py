import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_candidate_dashboard(client: AsyncClient) -> None:
    register_resp = await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Candidate User", "email": "candidate@test.com", "password": "SecureP@ss123"},
    )
    assert register_resp.status_code == 201

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "candidate@test.com", "password": "SecureP@ss123"},
    )
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.get("/api/v1/candidates/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "profile" in data
    assert data["full_name"] == "Candidate User"
    assert data["email"] == "candidate@test.com"


@pytest.mark.asyncio
async def test_candidate_profile_crud(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Profile Test", "email": "profile@test.com", "password": "SecureP@ss123"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "profile@test.com", "password": "SecureP@ss123"},
    )
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    get_resp = await client.get("/api/v1/candidates/profile", headers=headers)
    assert get_resp.status_code == 200

    update_resp = await client.put(
        "/api/v1/candidates/profile",
        json={"bio": "Experienced developer", "current_role": "Software Engineer", "location": "New York"},
        headers=headers,
    )
    assert update_resp.status_code == 200
    data = update_resp.json()
    assert data["bio"] == "Experienced developer"
    assert data["current_role"] == "Software Engineer"


@pytest.mark.asyncio
async def test_profile_completion(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Complete Test", "email": "complete@test.com", "password": "SecureP@ss123"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "complete@test.com", "password": "SecureP@ss123"},
    )
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    resp = await client.get("/api/v1/candidates/profile/completion", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "completion_percentage" in data
    assert "sections" in data
    assert "missing_sections" in data
    assert "recommendations" in data


@pytest.mark.asyncio
async def test_education_crud(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Edu Test", "email": "edu@test.com", "password": "SecureP@ss123"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "edu@test.com", "password": "SecureP@ss123"},
    )
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    create_resp = await client.post(
        "/api/v1/candidates/education",
        json={"institution": "MIT", "degree": "B.Sc. Computer Science", "cgpa": 3.8},
        headers=headers,
    )
    assert create_resp.status_code == 201
    edu_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/candidates/education", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    update_resp = await client.put(
        f"/api/v1/candidates/education/{edu_id}",
        json={"cgpa": 3.9},
        headers=headers,
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["cgpa"] == 3.9

    delete_resp = await client.delete(f"/api/v1/candidates/education/{edu_id}", headers=headers)
    assert delete_resp.status_code == 200


@pytest.mark.asyncio
async def test_experience_crud(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Exp Test", "email": "exp@test.com", "password": "SecureP@ss123"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "exp@test.com", "password": "SecureP@ss123"},
    )
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    create_resp = await client.post(
        "/api/v1/candidates/experience",
        json={"company": "Google", "job_title": "Software Engineer", "employment_type": "full_time"},
        headers=headers,
    )
    assert create_resp.status_code == 201
    exp_id = create_resp.json()["id"]

    list_resp = await client.get("/api/v1/candidates/experience", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    delete_resp = await client.delete(f"/api/v1/candidates/experience/{exp_id}", headers=headers)
    assert delete_resp.status_code == 200


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient) -> None:
    resp = await client.get("/api/v1/candidates/dashboard")
    assert resp.status_code in (401, 422)


@pytest.mark.asyncio
async def test_notifications(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"full_name": "Notif Test", "email": "notif@test.com", "password": "SecureP@ss123"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "notif@test.com", "password": "SecureP@ss123"},
    )
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    list_resp = await client.get("/api/v1/candidates/notifications", headers=headers)
    assert list_resp.status_code == 200

    unread_resp = await client.get("/api/v1/candidates/notifications/unread-count", headers=headers)
    assert unread_resp.status_code == 200
