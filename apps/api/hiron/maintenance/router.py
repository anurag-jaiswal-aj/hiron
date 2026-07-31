"""Thin REST router for Post-Launch Maintenance & Operational Diagnostics endpoints."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session
from hiron.maintenance.schemas import (
    AIQualityMetricsResponse,
    CachePurgeResponse,
    MaintenanceCleanupRequest,
    MaintenanceCleanupResponse,
    MaintenanceStatusResponse,
)
from hiron.maintenance.service import MaintenanceService
from hiron.users.models import User

router = APIRouter(prefix="/maintenance", tags=["Maintenance"])
maintenance_service = MaintenanceService()


@router.get(
    "/status",
    response_model=MaintenanceStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Post-launch system status & diagnostics",
    description="Returns overall system operational status and subsystem diagnostics. Requires org_admin role.",
)
async def get_maintenance_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MaintenanceStatusResponse:
    """Get subsystem operational health status."""
    return await maintenance_service.get_status(
        session=session,
        current_user_role=current_user.role,
    )


@router.post(
    "/cleanup",
    response_model=MaintenanceCleanupResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger maintenance cleanup",
    description="Executes maintenance cleanup operations (purging expired tokens/records). Requires org_admin role.",
)
async def execute_maintenance_cleanup(
    payload: MaintenanceCleanupRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> MaintenanceCleanupResponse:
    """Execute maintenance cleanup tasks."""
    return await maintenance_service.execute_cleanup(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        current_user_role=current_user.role,
        payload=payload,
    )


@router.post(
    "/cache/purge",
    response_model=CachePurgeResponse,
    status_code=status.HTTP_200_OK,
    summary="Purge in-memory application cache",
    description="Flushes in-memory LRU cache and resets metrics. Requires org_admin role.",
)
async def purge_maintenance_cache(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> CachePurgeResponse:
    """Purge in-memory LRU cache."""
    return await maintenance_service.purge_cache(
        session=session,
        current_user_role=current_user.role,
    )


@router.get(
    "/metrics/quality",
    response_model=AIQualityMetricsResponse,
    status_code=status.HTTP_200_OK,
    summary="AI quality & scoring diagnostics",
    description="Returns AI scoring quality metrics (average confidence, score variance). Requires org_admin role.",
)
async def get_ai_quality_metrics(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db_session),
) -> AIQualityMetricsResponse:
    """Get AI scoring quality diagnostics."""
    return await maintenance_service.get_ai_quality_metrics(
        session=session,
        tenant_id=current_user.tenant_id,
        current_user_role=current_user.role,
    )
