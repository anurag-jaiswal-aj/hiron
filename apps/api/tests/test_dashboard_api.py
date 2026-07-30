"""API integration tests for Dashboard & Analytics REST endpoints."""

import datetime
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.dashboard.router import get_dashboard_service
from hiron.dashboard.schemas import (
    AnalyticsAggregationResponse,
    DashboardMetrics,
    DashboardSummaryData,
    DashboardSummaryResponse,
    ScoreDistributionData,
    TimeSeriesPoint,
)
from hiron.main import create_app
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_dashboard_service() -> AsyncMock:
    """Fixture supplying mock DashboardService."""
    return AsyncMock()


@pytest.fixture
def client(mock_dashboard_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and DashboardService dependencies."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="recruiter@example.com",
        role="recruiter",
        is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    app.dependency_overrides[get_dashboard_service] = lambda: mock_dashboard_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_get_dashboard_summary_endpoint_success(
    client: TestClient, mock_dashboard_service: AsyncMock
) -> None:
    """Verify GET /api/v1/dashboard/summary returns 200 OK."""
    mock_dashboard_service.get_dashboard_summary.return_value = DashboardSummaryResponse(
        data=DashboardSummaryData(
            metrics=DashboardMetrics(
                open_jobs_count=3,
                total_candidates_count=20,
                scored_candidates_count=15,
                shortlisted_candidates_count=5,
                hired_candidates_count=1,
            ),
            pipeline_overview=[],
            score_distribution=ScoreDistributionData(
                high_fit_count=8,
                medium_fit_count=5,
                low_fit_count=2,
                total_scored=15,
                average_fit_score=81.2,
            ),
            recent_activity=[],
        )
    )

    response = client.get("/api/v1/dashboard/summary")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["metrics"]["openJobsCount"] == 3
    assert res_data["scoreDistribution"]["averageFitScore"] == 81.2


def test_get_analytics_aggregation_endpoint_success(
    client: TestClient, mock_dashboard_service: AsyncMock
) -> None:
    """Verify GET /api/v1/dashboard/analytics returns 200 OK with time-series points."""
    mock_dashboard_service.get_analytics_aggregation.return_value = AnalyticsAggregationResponse(
        data=[
            TimeSeriesPoint(
                date=datetime.date(2026, 7, 28),
                applications_count=5,
                scores_count=4,
            )
        ]
    )

    response = client.get("/api/v1/dashboard/analytics?startDate=2026-07-28&endDate=2026-07-28")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert len(res_data) == 1
    assert res_data[0]["applicationsCount"] == 5


def test_get_scoring_distribution_endpoint_success(
    client: TestClient, mock_dashboard_service: AsyncMock
) -> None:
    """Verify GET /api/v1/dashboard/scoring-distribution returns 200 OK."""
    mock_dashboard_service.get_score_distribution.return_value = ScoreDistributionData(
        high_fit_count=10,
        medium_fit_count=4,
        low_fit_count=1,
        total_scored=15,
        average_fit_score=85.0,
    )

    response = client.get("/api/v1/dashboard/scoring-distribution")

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["highFitCount"] == 10
    assert res_data["totalScored"] == 15
