"""Post-Launch Maintenance Subsystem unit and integration tests per Phase 19."""

import datetime
import uuid
from unittest.mock import AsyncMock, patch

import pytest

from hiron.maintenance.exceptions import MaintenancePermissionError
from hiron.maintenance.schemas import MaintenanceCleanupRequest
from hiron.maintenance.service import MaintenanceService
from hiron.scores.models import Score


@pytest.mark.asyncio
async def test_maintenance_status_org_admin_success() -> None:
    """Verify org_admin can retrieve subsystem maintenance operational status."""
    service = MaintenanceService()
    session = AsyncMock()

    with patch(
        "hiron.maintenance.service.check_database_connection", new_callable=AsyncMock
    ) as mock_db:
        mock_db.return_value = (True, 4.5)
        res = await service.get_status(session=session, current_user_role="org_admin")
        assert res.data.status == "operational"
        assert len(res.data.subsystems) >= 2


@pytest.mark.asyncio
async def test_maintenance_status_recruiter_forbidden() -> None:
    """Verify recruiter role receives MaintenancePermissionError on maintenance status check."""
    service = MaintenanceService()
    session = AsyncMock()

    with pytest.raises(MaintenancePermissionError):
        await service.get_status(session=session, current_user_role="recruiter")


@pytest.mark.asyncio
async def test_execute_maintenance_cleanup_success() -> None:
    """Verify org_admin can trigger maintenance cleanup operations."""
    service = MaintenanceService()
    session = AsyncMock()
    session.execute.return_value = AsyncMock(scalars=lambda: AsyncMock(all=list))

    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    res = await service.execute_cleanup(
        session=session,
        tenant_id=tenant_id,
        user_id=user_id,
        current_user_role="org_admin",
        payload=MaintenanceCleanupRequest(purge_expired_tokens=True),
    )
    assert res.data.cache_cleared is True
    assert res.data.expired_tokens_purged == 0


@pytest.mark.asyncio
async def test_purge_cache_success() -> None:
    """Verify org_admin can flush application in-memory cache."""
    service = MaintenanceService()
    session = AsyncMock()

    res = await service.purge_cache(session=session, current_user_role="org_admin")
    assert res.data.status == "purged"
    assert res.data.hit_count_reset is True


@pytest.mark.asyncio
async def test_ai_quality_metrics_empty() -> None:
    """Verify AI quality metrics default calculation when no scores exist."""
    service = MaintenanceService()
    session = AsyncMock()
    session.execute.return_value = AsyncMock(scalars=lambda: AsyncMock(all=list))

    tenant_id = uuid.uuid4()
    res = await service.get_ai_quality_metrics(
        session=session,
        tenant_id=tenant_id,
        current_user_role="org_admin",
    )
    assert res.data.total_evaluations_analyzed == 0
    assert res.data.average_confidence == 0.90


@pytest.mark.asyncio
async def test_ai_quality_metrics_with_scores() -> None:
    """Verify AI quality metrics calculation with score records."""
    service = MaintenanceService()
    session = AsyncMock()

    mock_score1 = Score(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        job_candidate_id=uuid.uuid4(),
        fit_score=90,
        confidence=0.85,
        breakdown={},
        explanation="High fit",
        prompt_name="candidate_fit_scoring",
        prompt_version="2.0.0",
        model_version="gpt-4o-2024-08-06",
        is_current=True,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    mock_score2 = Score(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        job_candidate_id=uuid.uuid4(),
        fit_score=70,
        confidence=0.75,
        breakdown={},
        explanation="Medium fit",
        prompt_name="candidate_fit_scoring",
        prompt_version="2.0.0",
        model_version="gpt-4o-2024-08-06",
        is_current=True,
        created_at=datetime.datetime.now(datetime.UTC),
    )

    session.execute.return_value = AsyncMock(
        scalars=lambda: AsyncMock(all=lambda: [mock_score1, mock_score2])
    )

    tenant_id = uuid.uuid4()
    res = await service.get_ai_quality_metrics(
        session=session,
        tenant_id=tenant_id,
        current_user_role="org_admin",
    )
    assert res.data.total_evaluations_analyzed == 2
    assert res.data.average_confidence == 0.80
    assert res.data.high_confidence_ratio == 0.50
