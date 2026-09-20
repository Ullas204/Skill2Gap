"""Queue a simulation execution through Celery.

Only the broker dispatch lives here. The synchronous fallback (no broker —
typical for dev and the test suite) is handled by the API layer running
``SimulationExecutionService.execute`` inline within the SAME request session,
so the freshly created execution row is guaranteed to be visible without any
cross-transaction commit races.
"""
import logging
import uuid

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _celery_available() -> bool:
    try:
        import redis as _redis
        settings = get_settings()
        r = _redis.from_url(settings.celery_broker_url, socket_connect_timeout=2)
        r.ping()
        r.close()
        return True
    except Exception:
        return False


def queue_simulation_execution(
    scenario_id: uuid.UUID,
    execution_id: uuid.UUID,
) -> dict:
    """Dispatch an execution to Celery. Returns ``{"status": "queued" | "queue_error"}``."""
    try:
        from app.workers.tasks import run_simulation

        result = run_simulation.delay(
            scenario_id=str(scenario_id),
            execution_id=str(execution_id),
        )
        logger.info(
            "Simulation queued: scenario=%s execution=%s task=%s",
            scenario_id,
            execution_id,
            result.id,
        )
        return {"status": "queued", "task_id": result.id}
    except Exception as exc:
        logger.exception(
            "Failed to queue simulation: scenario=%s execution=%s",
            scenario_id,
            execution_id,
        )
        return {"status": "queue_error", "task_id": None, "error": str(exc)[:500]}