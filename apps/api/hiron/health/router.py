"""Health check endpoints for load balancer and orchestrator readiness/liveness probes."""

from datetime import datetime, timezone
from typing import Dict

from fastapi import APIRouter, Response, status
from pydantic import Field

from hiron import __version__
from hiron.common.schemas import HironBaseModel

health_router = APIRouter(tags=["Health"])


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
    checks: Dict[str, SubsystemCheck] = Field(..., description="Map of subsystem health checks")


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
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@health_router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    status_code=status.HTTP_200_OK,
    responses={
        503: {"model": ReadinessResponse, "description": "Subsystems not ready for traffic"}
    },
    summary="Readiness check",
    description="Returns readiness status of database and Redis subsystems per API Contract §HEALTH-2.",
)
async def get_readiness(response: Response) -> ReadinessResponse:
    """Readiness probe checking real subsystem connectivity per API Contract §HEALTH-2.
    
    Accurately reports status: not_ready (503 Service Unavailable) until database and Redis
    connection management layers are initialized in subsequent implementation steps.
    """
    # Database and Redis connection layers will be attached here as they are implemented.
    # Prior to their initialization, falsely claiming readiness is prohibited.
    db_connected = False
    redis_connected = False

    if not (db_connected and redis_connected):
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="not_ready",
            checks={
                "database": SubsystemCheck(status="not_initialized", latency_ms=0.0),
                "redis": SubsystemCheck(status="not_initialized", latency_ms=0.0),
            },
        )

    return ReadinessResponse(
        status="ready",
        checks={
            "database": SubsystemCheck(status="up", latency_ms=0.0),
            "redis": SubsystemCheck(status="up", latency_ms=0.0),
        },
    )
