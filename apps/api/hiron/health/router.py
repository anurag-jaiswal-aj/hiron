"""Health check endpoints for load balancer and orchestrator readiness/liveness probes."""

from datetime import UTC, datetime

from fastapi import APIRouter, Response, status
from pydantic import Field

from hiron import __version__
from hiron.common.schemas import HironBaseModel
from hiron.core.database import check_database_connection

health_router = APIRouter(tags=["Health"])
router = health_router


class HealthResponse(HironBaseModel):
    """Response model for liveness check per API Contract §HEALTH-1."""

    status: str = Field(default="healthy", description="Application status string")
    version: str = Field(default=__version__, description="Application semantic version")
    timestamp: str = Field(..., description="Current UTC timestamp ISO 8601")


class SubsystemCheck(HironBaseModel):
    """Subsystem health status check item."""

    status: str = Field(..., description="Subsystem status: up | down | not_initialized")
    latency_ms: float = Field(..., description="Check ping latency in milliseconds")


class ReadinessResponse(HironBaseModel):
    """Response model for readiness check per API Contract §HEALTH-2."""

    status: str = Field(..., description="Overall readiness: ready | not_ready")
    checks: dict[str, SubsystemCheck] = Field(..., description="Map of subsystem health checks")


@health_router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health check (liveness probe)",
    description="Returns application health status and version. Used for load balancer liveness probes.",
)
async def get_health() -> HealthResponse:
    """Liveness probe returning application version and timestamp per API Contract §HEALTH-1."""
    return HealthResponse(
        status="healthy",
        version=__version__,
        timestamp=datetime.now(UTC).isoformat(),
    )


@health_router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {"model": ReadinessResponse, "description": "Subsystems not ready for traffic"},
    },
    summary="Readiness check",
    description="Returns readiness status of database and Redis subsystems per API Contract §HEALTH-2.",
)
async def get_readiness(response: Response) -> ReadinessResponse:
    """Readiness probe checking real PostgreSQL connectivity per API Contract §HEALTH-2."""
    db_healthy, db_latency = await check_database_connection()

    db_status_str = "up" if db_healthy else "down"

    # Redis will participate in readiness gating once the Redis service layer is introduced.
    redis_status_str = "not_initialized"

    # Overall readiness reflects active implemented infrastructure components (PostgreSQL)
    is_overall_ready = db_healthy

    if not is_overall_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status="ready" if is_overall_ready else "not_ready",
        checks={
            "database": SubsystemCheck(status=db_status_str, latency_ms=db_latency),
            "redis": SubsystemCheck(status=redis_status_str, latency_ms=0.0),
        },
    )
