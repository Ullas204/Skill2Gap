import time

from fastapi import APIRouter

from app.core.config import get_settings
from app.core.logging import get_logger
from app.db.session import async_session_factory

router = APIRouter(tags=["health"])
logger = get_logger(__name__)
settings = get_settings()


@router.get("/health")
async def health_check():
    db_ok = False
    try:
        async with async_session_factory() as session:
            await session.execute(
                __import__("sqlalchemy").text("SELECT 1"),
            )
            db_ok = True
    except Exception as exc:
        logger.error("Health check DB failure: %s", exc)

    return {
        "status": "healthy" if db_ok else "degraded",
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "connected" if db_ok else "disconnected",
        "timestamp": time.time(),
    }


@router.get("/health/ready")
async def readiness_check():
    db_ok = False
    try:
        async with async_session_factory() as session:
            await session.execute(
                __import__("sqlalchemy").text("SELECT 1"),
            )
            db_ok = True
    except Exception as exc:
        logger.error("Readiness check DB failure: %s", exc)

    if not db_ok:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="Database unavailable")

    return {"status": "ready"}
