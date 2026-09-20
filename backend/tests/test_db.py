import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Role, User


@pytest.mark.asyncio
async def test_create_user(session: AsyncSession) -> None:
    user = User(
        full_name="Database User",
        email="db@example.com",
        password_hash="hashed_password",
    )
    session.add(user)
    await session.flush()

    assert user.id is not None
    assert user.is_active is True
    assert user.is_verified is False


@pytest.mark.asyncio
async def test_create_role(session: AsyncSession) -> None:
    role = Role(name="test_role_unique", description="Test role")
    session.add(role)
    await session.flush()

    assert role.id is not None
    assert role.name == "test_role_unique"


@pytest.mark.asyncio
async def test_database_connection(session: AsyncSession) -> None:
    result = await session.execute(text("SELECT 1"))
    assert result.scalar() == 1
