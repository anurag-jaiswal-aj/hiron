"""Unit tests for DashboardRepository metric counts, score distribution calculations, and time-series aggregation."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from hiron.dashboard.repository import DashboardRepository


@pytest.mark.asyncio
async def test_get_open_jobs_count_returns_int() -> None:
    """Verify get_open_jobs_count returns integer count."""
    repo = DashboardRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = 5
    session.execute.return_value = mock_result

    count = await repo.get_open_jobs_count(session, tenant_id)

    assert count == 5
    session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_score_distribution_stats_computes_breakdown() -> None:
    """Verify get_score_distribution_stats accurately groups high, medium, and low scores."""
    repo = DashboardRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    mock_result = MagicMock()
    mock_row = MagicMock()
    mock_row.high = 2
    mock_row.medium = 2
    mock_row.low = 1
    mock_row.total = 5
    mock_row.avg = 73.0
    mock_result.one.return_value = mock_row
    session.execute.return_value = mock_result

    high, medium, low, total, avg = await repo.get_score_distribution_stats(session, tenant_id)

    assert high == 2
    assert medium == 2
    assert low == 1
    assert total == 5
    assert avg == 73.0
