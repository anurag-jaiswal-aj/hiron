"""API integration tests for GET /api/v1/performance/benchmark REST endpoint."""

import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.main import create_app
from hiron.performance.router import get_performance_service
from hiron.performance.schemas import (
    CachePerformanceMetrics,
    LatencyBenchmark,
    PerformanceReportData,
    PerformanceReportResponse,
)
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_perf_service() -> AsyncMock:
    """Fixture supplying mock PerformanceService."""
    return AsyncMock()


@pytest.fixture
def client(mock_perf_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and PerformanceService dependencies."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="admin@example.com",
        role="org_admin",
        is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    app.dependency_overrides[get_performance_service] = lambda: mock_perf_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_get_performance_benchmark_endpoint_success(
    client: TestClient, mock_perf_service: AsyncMock
) -> None:
    """Verify GET /api/v1/performance/benchmark returns 200 OK per Phase 15."""
    mock_perf_service.run_performance_benchmarks.return_value = PerformanceReportResponse(
        data=PerformanceReportData(
            benchmarks=[
                LatencyBenchmark(
                    target_name="Dashboard Summary Aggregations",
                    latency_ms=45.2,
                    threshold_ms=500.0,
                    status="PASSED",
                )
            ],
            cache_stats=CachePerformanceMetrics(
                hits=15,
                misses=5,
                total_requests=20,
                hit_rate=0.75,
                cached_entries_count=8,
            ),
            overall_status="PASSED",
        )
    )

    response = client.get("/api/v1/performance/benchmark")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["overallStatus"] == "PASSED"
    assert len(res_data["benchmarks"]) == 1
    assert res_data["cacheStats"]["hitRate"] == 0.75
