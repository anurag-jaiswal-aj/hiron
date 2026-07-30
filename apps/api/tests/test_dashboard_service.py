"""Service unit tests for DashboardService summary aggregations, date-range time series generation, and score stats."""

import datetime
import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.dashboard.schemas import (
    AnalyticsAggregationResponse,
    DashboardSummaryResponse,
)
from hiron.dashboard.service import DashboardService


@pytest.mark.asyncio
async def test_get_dashboard_summary_compiles_data() -> None:
    """Verify get_dashboard_summary calls repo methods and returns structured summary."""
    repo = AsyncMock()
    service = DashboardService(dashboard_repository=repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()

    repo.get_open_jobs_count.return_value = 4
    repo.get_total_candidates_count.return_value = 50
    repo.get_scored_candidates_count.return_value = 30
    repo.get_shortlisted_candidates_count.return_value = 10
    repo.get_hired_candidates_count.return_value = 2
    repo.get_top_jobs_pipeline_overviews.return_value = []
    repo.get_score_distribution_stats.return_value = (15, 10, 5, 30, 78.5)
    repo.get_recent_stage_activities.return_value = []

    res = await service.get_dashboard_summary(session, tenant_id)

    assert isinstance(res, DashboardSummaryResponse)
    assert res.data.metrics.open_jobs_count == 4
    assert res.data.metrics.total_candidates_count == 50
    assert res.data.score_distribution.high_fit_count == 15
    assert res.data.score_distribution.average_fit_score == 78.5


@pytest.mark.asyncio
async def test_get_analytics_aggregation_fills_date_range() -> None:
    """Verify get_analytics_aggregation generates a continuous daily time-series points list."""
    repo = AsyncMock()
    service = DashboardService(dashboard_repository=repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    start_date = datetime.date(2026, 7, 1)
    end_date = datetime.date(2026, 7, 5)

    repo.get_application_counts_by_date.return_value = {datetime.date(2026, 7, 2): 5}
    repo.get_score_counts_by_date.return_value = {datetime.date(2026, 7, 2): 3}

    res = await service.get_analytics_aggregation(
        session=session,
        tenant_id=tenant_id,
        start_date=start_date,
        end_date=end_date,
    )

    assert isinstance(res, AnalyticsAggregationResponse)
    assert len(res.data) == 5  # July 1, 2, 3, 4, 5
    assert res.data[0].date == datetime.date(2026, 7, 1)
    assert res.data[0].applications_count == 0
    assert res.data[1].date == datetime.date(2026, 7, 2)
    assert res.data[1].applications_count == 5
    assert res.data[1].scores_count == 3
