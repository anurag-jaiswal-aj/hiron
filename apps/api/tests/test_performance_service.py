"""Service unit tests for PerformanceService benchmark execution and NFR compliance verification."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.performance.schemas import PerformanceReportResponse
from hiron.performance.service import PerformanceService


@pytest.mark.asyncio
async def test_run_performance_benchmarks_success() -> None:
    """Verify PerformanceService measures latency and compiles report."""
    dashboard_repo = AsyncMock()
    service = PerformanceService(dashboard_repository=dashboard_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()

    dashboard_repo.get_open_jobs_count.return_value = 10
    dashboard_repo.get_total_candidates_count.return_value = 150
    dashboard_repo.get_scored_candidates_count.return_value = 120
    dashboard_repo.get_shortlisted_candidates_count.return_value = 25
    dashboard_repo.get_top_jobs_pipeline_overviews.return_value = []
    dashboard_repo.get_score_distribution_stats.return_value = (80, 30, 10)

    report = await service.run_performance_benchmarks(session, tenant_id)

    assert isinstance(report, PerformanceReportResponse)
    assert len(report.data.benchmarks) == 3
    assert report.data.overall_status in ("PASSED", "WARNING")
    assert report.data.benchmarks[0].target_name == "Dashboard Summary Aggregations"
    assert report.data.benchmarks[0].threshold_ms == 500.0
