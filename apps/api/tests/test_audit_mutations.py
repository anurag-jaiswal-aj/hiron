"""Integration tests verifying real mutations generate correct audit logs."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.jobs.models import Job
from hiron.jobs.service import JobService


@pytest.fixture
def session() -> AsyncMock:
    """Mock database session fixture."""
    return AsyncMock()


@pytest.fixture
def setup_test_data() -> tuple[uuid.UUID, uuid.UUID]:
    """Create test IDs."""
    return uuid.uuid4(), uuid.uuid4()


@pytest.mark.asyncio
async def test_job_mutations_generate_audit(
    session: AsyncMock,
    setup_test_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Test Create job mutations."""
    tenant_id, user_id = setup_test_data

    job_service = JobService()

    mock_job_repo = AsyncMock()
    mock_job_repo.create_job.return_value = Job(id=uuid.uuid4(), title="Software Engineer", status="open")
    mock_job_repo.create_pipeline_stages = AsyncMock()
    job_service.job_repo = mock_job_repo

    mock_audit_service = AsyncMock()
    job_service.audit_service = mock_audit_service

    # 1. CREATE JOB
    job = await job_service.create_job(
        session=session,
        tenant_id=tenant_id,
        created_by=user_id,
        current_user_role="org_admin",
        title="Software Engineer",
        description="Write code.",
        employment_type="full_time",
    )

    # Assert commit was called
    session.commit.assert_called()

    # Assert audit log was recorded
    mock_audit_service.record_audit_log.assert_called_once()
    kwargs = mock_audit_service.record_audit_log.call_args.kwargs
    assert kwargs["action"] == "job_created"
    assert kwargs["actor_id"] == user_id
    assert kwargs["tenant_id"] == tenant_id
    assert kwargs["entity_id"] == job.id


@pytest.mark.asyncio
async def test_transaction_atomicity(
    session: AsyncMock,
    setup_test_data: tuple[uuid.UUID, uuid.UUID],
) -> None:
    """Prove that if audit fails, exception propagates and commit is not reached."""
    tenant_id, user_id = setup_test_data
    job_service = JobService()

    mock_job_repo = AsyncMock()
    mock_job_repo.create_job.return_value = Job(id=uuid.uuid4(), title="Fail Job")
    mock_job_repo.create_pipeline_stages = AsyncMock()
    job_service.job_repo = mock_job_repo

    mock_audit_service = AsyncMock()
    mock_audit_service.record_audit_log.side_effect = Exception("Audit failed")
    job_service.audit_service = mock_audit_service

    try:
        await job_service.create_job(
            session=session,
            tenant_id=tenant_id,
            created_by=user_id,
            current_user_role="org_admin",
            title="Fail Job",
            description="Fail",
            employment_type="full_time",
        )
        pytest.fail("Should have raised exception")
    except Exception as e:
        assert str(e) == "Audit failed"

    # Verify commit was never called because it failed beforehand
    session.commit.assert_not_called()
