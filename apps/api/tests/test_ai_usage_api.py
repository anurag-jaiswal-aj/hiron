"""API integration tests for USAGE-1 and USAGE-2 REST endpoints."""

import datetime
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.ai_usage.router import get_ai_usage_service
from hiron.ai_usage.schemas import (
    AIUsageLogItem,
    AIUsageLogPagination,
    AIUsageLogsResponse,
    AIUsageSummaryData,
    AIUsageSummaryResponse,
    DailyUsagePoint,
    OperationUsageBreakdown,
)
from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.main import create_app
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_ai_usage_service() -> AsyncMock:
    """Fixture supplying mock AIUsageService."""
    return AsyncMock()


@pytest.fixture
def client(mock_ai_usage_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and AIUsageService dependencies."""
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
    app.dependency_overrides[get_ai_usage_service] = lambda: mock_ai_usage_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_get_ai_usage_summary_endpoint_success(
    client: TestClient, mock_ai_usage_service: AsyncMock
) -> None:
    """Verify GET /api/v1/ai-usage/summary returns 200 OK per §USAGE-1."""
    mock_ai_usage_service.get_usage_summary.return_value = AIUsageSummaryResponse(
        data=AIUsageSummaryData(
            total_cost_usd=12.50,
            total_tokens=450000,
            total_operations=800,
            cache_hit_rate=0.42,
            by_operation=[
                OperationUsageBreakdown(
                    operation="candidate_scoring",
                    count=500,
                    cost_usd=10.00,
                    avg_latency_ms=2500,
                )
            ],
            by_day=[DailyUsagePoint(date="2026-07-28", cost_usd=2.50, operations=120)],
        )
    )

    response = client.get("/api/v1/ai-usage/summary?period=30d")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["totalCostUsd"] == 12.50
    assert res_data["cacheHitRate"] == 0.42
    assert len(res_data["byOperation"]) == 1


def test_list_ai_usage_logs_endpoint_success(
    client: TestClient, mock_ai_usage_service: AsyncMock
) -> None:
    """Verify GET /api/v1/ai-usage/logs returns 200 OK per §USAGE-2."""
    log_id = uuid.uuid4()

    mock_ai_usage_service.list_usage_logs.return_value = AIUsageLogsResponse(
        data=[
            AIUsageLogItem(
                id=log_id,
                operation="resume_parsing",
                model_version="gemini-1.5-flash",
                prompt_name="resume_parser_v1",
                input_tokens=1500,
                output_tokens=300,
                total_tokens=1800,
                cost_usd=0.005,
                latency_ms=1800,
                status="success",
                is_cache_hit=False,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        ],
        pagination=AIUsageLogPagination(has_more=False, next_cursor=None, total_count=1),
    )

    response = client.get("/api/v1/ai-usage/logs")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert len(res_data) == 1
    assert res_data[0]["operation"] == "resume_parsing"
    assert res_data[0]["totalTokens"] == 1800
