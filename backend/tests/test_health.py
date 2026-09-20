import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "environment" in data
    assert "database" in data


@pytest.mark.asyncio
async def test_readiness_endpoint(client: AsyncClient, session) -> None:
    from unittest.mock import AsyncMock, patch
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def mock_session_factory():
        yield session

    with patch("app.api.v1.health.async_session_factory", mock_session_factory):
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
