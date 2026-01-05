"""Health check endpoints."""

import asyncio
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.models import APIKey
from app.db.session import get_db_no_commit
from app.health.schemas import HealthResponse, ReadinessResponse

# Health check query timeout in seconds
HEALTH_CHECK_TIMEOUT = 5.0

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/live",
    response_model=HealthResponse,
    summary="Liveness probe",
    description="Check if the application is running",
)
async def liveness() -> HealthResponse:
    """Liveness probe - is the application running?"""
    return HealthResponse(status="ok")


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description="Check if the application is ready to serve traffic",
    responses={
        status.HTTP_200_OK: {"description": "Service is ready"},
        status.HTTP_503_SERVICE_UNAVAILABLE: {"description": "Service is not ready"},
    },
)
async def readiness(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db_no_commit)],
) -> ReadinessResponse:
    """Readiness probe - is the application ready to serve traffic?

    Checks database connectivity and table access, returns overall status.
    Returns 503 if any check fails (for Kubernetes compatibility).
    """
    checks: dict[str, str] = {}

    # Check database connectivity and table access with timeout
    try:
        # Verify we can query the api_keys table (not just ping the database)
        # Use asyncio.wait_for to enforce a timeout on the health check query
        result = await asyncio.wait_for(
            db.execute(select(func.count(APIKey.id))),
            timeout=HEALTH_CHECK_TIMEOUT,
        )
        result.scalar()  # Ensure result is fetched
        checks["database"] = "ok"
    except TimeoutError:
        logger.warning(
            "Database health check timed out",
            extra={"timeout_seconds": HEALTH_CHECK_TIMEOUT},
        )
        checks["database"] = "timeout"
    except SQLAlchemyError as e:
        logger.warning("Database health check failed", extra={"error": str(e)})
        checks["database"] = "error"

    # Determine overall status
    all_ok = all(v == "ok" for v in checks.values())
    overall_status = "ok" if all_ok else "degraded"

    # Return 503 if not ready (Kubernetes expects this)
    if not all_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(status=overall_status, checks=checks)
