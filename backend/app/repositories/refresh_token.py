import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import RefreshToken
from app.repositories.base import BaseRepository


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, RefreshToken)

    async def store(self, user_id: uuid.UUID, token: str, expires_at: datetime) -> RefreshToken:
        if expires_at.tzinfo is not None:
            expires_at = expires_at.replace(tzinfo=None)
        rt = RefreshToken(
            user_id=user_id,
            token_hash=_hash_token(token),
            expires_at=expires_at,
            is_revoked=False,
        )
        self._session.add(rt)
        await self._session.flush()
        return rt

    async def is_valid(self, token: str) -> bool:
        token_hash = _hash_token(token)
        stmt = select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,  # noqa: E712
        )
        result = await self._session.execute(stmt)
        rt = result.scalar_one_or_none()
        if not rt:
            return False
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        if rt.expires_at < now_utc:
            return False
        return True

    async def revoke(self, token: str) -> bool:
        token_hash = _hash_token(token)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.is_revoked == False)  # noqa: E712
            .values(is_revoked=True)
        )
        result = await self._session.execute(stmt)
        return result.rowcount > 0

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> int:
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)  # noqa: E712
            .values(is_revoked=True)
        )
        result = await self._session.execute(stmt)
        return result.rowcount

    async def cleanup_expired(self) -> int:
        from sqlalchemy import delete

        stmt = delete(RefreshToken).where(
            RefreshToken.expires_at < datetime.now(timezone.utc).replace(tzinfo=None),
        )
        result = await self._session.execute(stmt)
        return result.rowcount
