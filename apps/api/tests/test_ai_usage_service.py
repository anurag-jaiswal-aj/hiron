"""Service unit tests for AIUsageService org_admin RBAC security and period calculation."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.ai_usage.exceptions import (
    AIUsageValidationError,
    InsufficientAIUsagePermissionsError,
)
from hiron.ai_usage.schemas import AIUsageSummaryResponse
from hiron.ai_usage.service import AIUsageService


@pytest.mark.asyncio
async def test_recruiter_access_raises_403() -> None:
    """Verify recruiter role cannot access AI usage summary analytics."""
    service = AIUsageService()
    session = AsyncMock()

    with pytest.raises(
        InsufficientAIUsagePermissionsError, match="not authorized to access AI usage analytics"
    ):
        await service.get_usage_summary(
            session=session,
            tenant_id=uuid.uuid4(),
            user_role="recruiter",
            period="30d",
        )


@pytest.mark.asyncio
async def test_invalid_period_raises_validation_error() -> None:
    """Verify invalid period string raises AIUsageValidationError."""
    service = AIUsageService()
    session = AsyncMock()

    with pytest.raises(AIUsageValidationError, match="Invalid period parameter"):
        await service.get_usage_summary(
            session=session,
            tenant_id=uuid.uuid4(),
            user_role="org_admin",
            period="180d",
        )


@pytest.mark.asyncio
async def test_org_admin_summary_success() -> None:
    """Verify org_admin receives structured AI usage summary payload."""
    repo = AsyncMock()
    service = AIUsageService(ai_usage_repository=repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()

    repo.get_summary_metrics.return_value = (45.67, 1500000, 3000, 0.35)
    repo.get_operation_breakdown.return_value = [("candidate_scoring", 2000, 35.4, 3200)]
    repo.get_daily_breakdown.return_value = [("2026-07-28", 3.45, 150)]

    res = await service.get_usage_summary(
        session=session,
        tenant_id=tenant_id,
        user_role="org_admin",
        period="30d",
    )

    assert isinstance(res, AIUsageSummaryResponse)
    assert res.data.total_cost_usd == 45.67
    assert res.data.total_tokens == 1500000
    assert res.data.cache_hit_rate == 0.35
    assert len(res.data.by_operation) == 1
    assert res.data.by_operation[0].operation == "candidate_scoring"
