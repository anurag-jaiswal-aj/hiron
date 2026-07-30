"""Thin FastAPI router for Dashboard & Analytics per API Contract and IMPLEMENTATION_ROADMAP.md Phase 12."""

import datetime

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.dashboard.schemas import (
    AnalyticsAggregationResponse,
    DashboardSummaryResponse,
    JobPipelineOverview,
    ScoreDistributionData,
)
from hiron.dashboard.service import DashboardService
from hiron.users.models import User

router = APIRouter(tags=["Dashboard & Analytics"])


def get_dashboard_service() -> DashboardService:
    """Dependency provider for DashboardService."""
    return DashboardService()


@router.get(
    "/dashboard/summary",
    response_model=DashboardSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Dashboard Summary",
)
async def get_dashboard_summary_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: DashboardService = Depends(get_dashboard_service),
) -> DashboardSummaryResponse:
    """Get complete dashboard overview metrics, top job pipelines, score distribution, and recent activity log feed."""
    return await service.get_dashboard_summary(
        session=session,
        tenant_id=current_user.tenant_id,
    )


@router.get(
    "/dashboard/analytics",
    response_model=AnalyticsAggregationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Time-Series Analytics Aggregations",
)
async def get_analytics_aggregation_endpoint(
    start_date: datetime.date | None = Query(default=None, alias="startDate"),
    end_date: datetime.date | None = Query(default=None, alias="endDate"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: DashboardService = Depends(get_dashboard_service),
) -> AnalyticsAggregationResponse:
    """Get time-series daily aggregations for applications and score evaluations filtered by date range."""
    return await service.get_analytics_aggregation(
        session=session,
        tenant_id=current_user.tenant_id,
        start_date=start_date,
        end_date=end_date,
    )


@router.get(
    "/dashboard/pipeline-overview",
    response_model=list[JobPipelineOverview],
    status_code=status.HTTP_200_OK,
    summary="Get Job Pipeline Overview",
)
async def get_pipeline_overview_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: DashboardService = Depends(get_dashboard_service),
) -> list[JobPipelineOverview]:
    """Get pipeline stage candidate counts per open job."""
    return await service.get_pipeline_overviews(
        session=session,
        tenant_id=current_user.tenant_id,
    )


@router.get(
    "/dashboard/scoring-distribution",
    response_model=ScoreDistributionData,
    status_code=status.HTTP_200_OK,
    summary="Get AI Scoring Distribution",
)
async def get_scoring_distribution_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: DashboardService = Depends(get_dashboard_service),
) -> ScoreDistributionData:
    """Get AI candidate fit score distribution statistics (high, medium, low match counts and average score)."""
    return await service.get_score_distribution(
        session=session,
        tenant_id=current_user.tenant_id,
    )
