"""Health check response schemas."""

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Response for liveness probe."""

    status: str = Field(..., description="Health status (ok, error)")


class ReadinessResponse(BaseModel):
    """Response for readiness probe with dependency checks."""

    status: str = Field(..., description="Overall status (ok, degraded, error)")
    checks: dict[str, str] = Field(
        default_factory=dict,
        description="Individual dependency check results",
    )
