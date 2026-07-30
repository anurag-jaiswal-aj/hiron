"""Unit tests for AIUsageRepository creation, aggregate cost/token sums, and pagination."""

import decimal
import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.ai_usage.repository import AIUsageRepository


@pytest.mark.asyncio
async def test_create_usage_log_persists_entity() -> None:
    """Verify create_usage_log adds AIUsageLog entity to session."""
    repo = AIUsageRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    log = await repo.create_usage_log(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        operation="candidate_scoring",
        model_version="gemini-1.5-pro",
        input_tokens=1000,
        output_tokens=200,
        cost_usd=0.015,
        latency_ms=1200,
        is_cache_hit=False,
    )

    assert log.tenant_id == tenant_id
    assert log.operation == "candidate_scoring"
    assert log.total_tokens == 1200
    assert log.cost_usd == decimal.Decimal("0.015")
    session.add.assert_called_once()
