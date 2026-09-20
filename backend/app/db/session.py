from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
logger = get_logger(__name__)

is_sqlite = "sqlite" in str(settings.database_url)

engine = create_async_engine(
    str(settings.database_url),
    echo=settings.database_echo,
    poolclass=NullPool if is_sqlite else None,
    connect_args={"check_same_thread": False} if is_sqlite else {},
)

async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            logger.debug("Rolling back session due to exception")
            try:
                await session.rollback()
            except Exception:
                logger.warning("Session rollback itself failed")
            raise
        finally:
            await session.close()
