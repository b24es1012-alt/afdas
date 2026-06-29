"""
Health check endpoint — verifies all system components.
"""

from fastapi import APIRouter
from datetime import datetime

from database.connection import DatabaseManager
from cache.manager import CacheManager
from utils.logger import api_logger as logger

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def health_check():
    """
    Full system health check.
    Verifies: PostgreSQL, Redis, PostGIS.
    """
    checks = {}

    # Database check
    try:
        db_health = await DatabaseManager.health_check()
        checks["database"] = db_health
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    # Redis check
    try:
        redis_health = await CacheManager.health_check()
        checks["redis"] = redis_health
    except Exception as e:
        checks["redis"] = {"status": "unhealthy", "error": str(e)}

    # Overall status
    all_healthy = all(
        c.get("status") == "healthy" for c in checks.values()
    )

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
    }


@router.get("/ping")
async def ping():
    """Simple liveness probe."""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}
