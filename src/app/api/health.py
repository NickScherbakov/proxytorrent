"""Health check endpoint."""
import logging
import time
from typing import Any

from fastapi import APIRouter

from app.core.config import settings
from app.models.schemas import HealthResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

# Track service start time
_start_time = time.time()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint.

    Returns service status and component health.
    """
    checks: dict[str, Any] = {}

    # Check database
    try:
        from app.core.database import engine

        async with engine.connect() as conn:
            await conn.execute("SELECT 1")
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    # Check storage
    try:
        settings.storage.base_path.exists()
        checks["storage"] = {"status": "healthy"}
    except Exception as e:
        logger.error(f"Storage health check failed: {e}")
        checks["storage"] = {"status": "unhealthy", "error": str(e)}

    # Check task queue
    try:
        from app.tasks.queue import get_task_queue

        queue = get_task_queue()
        checks["task_queue"] = {
            "status": "healthy" if queue.running else "stopped",
            "queue_size": queue.queue.qsize(),
        }
    except Exception as e:
        logger.error(f"Task queue health check failed: {e}")
        checks["task_queue"] = {"status": "unhealthy", "error": str(e)}

    # Overall status
    overall_status = "healthy"
    for check in checks.values():
        if isinstance(check, dict) and check.get("status") != "healthy":
            overall_status = "degraded"
            break

    return HealthResponse(
        status=overall_status,
        version=settings.app_version,
        uptime=time.time() - _start_time,
        checks=checks,
    )
