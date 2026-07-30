"""Thin FastAPI router for AI Usage Monitoring per API Contract §USAGE-1..2."""

import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.ai_usage.schemas import AIUsageLogsResponse, AIUsageSummaryResponse
from hiron.ai_usage.service import AIUsageService
from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.users.models import User

router = APIRouter(tags=["AI Usage Monitoring"])


def get_ai_usage_service() -> AIUsageService:
    """Dependency provider for AIUsageService."""
    return AIUsageService()


@router.get(
    "/ai-usage/summary",
    response_model=AIUsageSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI Usage Summary (USAGE-1)",
)
async def get_ai_usage_summary_endpoint(
    period: str = Query(default="30d"),
    group_by: str = Query(default="day", alias="groupBy"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: AIUsageService = Depends(get_ai_usage_service),
) -> AIUsageSummaryResponse:
    """Get aggregated AI usage and cost data for the tenant per §USAGE-1."""
    return await service.get_usage_summary(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        period=period,
        group_by=group_by,
    )


@router.get(
    "/ai-usage/logs",
    response_model=AIUsageLogsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get AI Usage Details (USAGE-2)",
)
async def list_ai_usage_logs_endpoint(
    operation: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    start_date: datetime.datetime | None = Query(default=None, alias="startDate"),
    end_date: datetime.datetime | None = Query(default=None, alias="endDate"),
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: AIUsageService = Depends(get_ai_usage_service),
) -> AIUsageLogsResponse:
    """List individual AI operation records per §USAGE-2."""
    return await service.list_usage_logs(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        operation=operation,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        limit=limit,
        cursor=cursor,
    )
