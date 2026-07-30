"""Unit tests for JobRepository CRUD operations, filters, pagination, and pipeline stage persistence."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from hiron.jobs.models import Job, PipelineStage
from hiron.jobs.repository import JobRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_job_success(mock_session: AsyncMock) -> None:
    """Verify create_job adds entity to session and flushes."""
    repo = JobRepository()
    tenant_id = uuid.uuid4()
    job = Job(
        tenant_id=tenant_id,
        title="Senior Backend Engineer",
        description="Job description text",
    )

    created = await repo.create_job(mock_session, job)
    assert created == job
    mock_session.add.assert_called_once_with(job)
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_job_by_id_success(mock_session: AsyncMock) -> None:
    """Verify get_job_by_id executes select query and returns Job entity."""
    repo = JobRepository()
    job_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    mock_job = Job(id=job_id, tenant_id=tenant_id, title="Backend Engineer", description="Desc")
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_job
    mock_session.execute.return_value = mock_res

    res = await repo.get_job_by_id(mock_session, job_id=job_id, tenant_id=tenant_id)
    assert res == mock_job
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_job_by_id_returns_none_when_not_found(mock_session: AsyncMock) -> None:
    """Verify get_job_by_id returns None when job does not exist."""
    repo = JobRepository()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = None
    mock_session.execute.return_value = mock_res

    res = await repo.get_job_by_id(mock_session, job_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    assert res is None


@pytest.mark.asyncio
async def test_list_jobs_by_tenant(mock_session: AsyncMock) -> None:
    """Verify list_jobs returns items and total count tuple."""
    repo = JobRepository()
    tenant_id = uuid.uuid4()
    job1 = Job(id=uuid.uuid4(), tenant_id=tenant_id, title="Job 1", description="Desc 1")
    job2 = Job(id=uuid.uuid4(), tenant_id=tenant_id, title="Job 2", description="Desc 2")

    mock_count_res = MagicMock()
    mock_count_res.scalar_one.return_value = 2

    mock_items_res = MagicMock()
    mock_items_res.scalars.return_value.all.return_value = [job1, job2]

    mock_session.execute.side_effect = [mock_count_res, mock_items_res]

    jobs, total = await repo.list_jobs(mock_session, tenant_id=tenant_id, limit=10, offset=0)
    assert len(jobs) == 2
    assert total == 2
    assert jobs[0] == job1
    assert jobs[1] == job2


@pytest.mark.asyncio
async def test_update_job_success(mock_session: AsyncMock) -> None:
    """Verify update_job modifies fields and flushes session."""
    repo = JobRepository()
    job_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    mock_job = Job(id=job_id, tenant_id=tenant_id, title="Old Title", description="Desc")
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_job
    mock_session.execute.return_value = mock_res

    updated = await repo.update_job(
        mock_session, job_id=job_id, tenant_id=tenant_id, title="New Title"
    )
    assert updated is not None
    assert updated.title == "New Title"
    mock_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_archive_job_success(mock_session: AsyncMock) -> None:
    """Verify archive_job sets is_archived to True."""
    repo = JobRepository()
    job_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    mock_job = Job(
        id=job_id, tenant_id=tenant_id, title="Title", description="Desc", is_archived=False
    )
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_job
    mock_session.execute.return_value = mock_res

    archived = await repo.archive_job(mock_session, job_id=job_id, tenant_id=tenant_id)
    assert archived is not None
    assert archived.is_archived is True


@pytest.mark.asyncio
async def test_delete_job_success(mock_session: AsyncMock) -> None:
    """Verify delete_job deletes entity from session."""
    repo = JobRepository()
    job_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    mock_job = Job(id=job_id, tenant_id=tenant_id, title="Title", description="Desc")
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = mock_job
    mock_session.execute.return_value = mock_res

    deleted = await repo.delete_job(mock_session, job_id=job_id, tenant_id=tenant_id)
    assert deleted is True
    mock_session.delete.assert_called_once_with(mock_job)
    mock_session.flush.assert_awaited()


@pytest.mark.asyncio
async def test_create_pipeline_stages_and_list(mock_session: AsyncMock) -> None:
    """Verify batch creation and listing of pipeline stages."""
    repo = JobRepository()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    s1 = PipelineStage(tenant_id=tenant_id, job_id=job_id, name="Applied", position=1)
    s2 = PipelineStage(tenant_id=tenant_id, job_id=job_id, name="Interview", position=2)

    created = await repo.create_pipeline_stages(mock_session, [s1, s2])
    assert len(created) == 2
    mock_session.add_all.assert_called_once_with([s1, s2])

    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [s1, s2]
    mock_session.execute.return_value = mock_res

    stages = await repo.list_pipeline_stages(mock_session, job_id=job_id, tenant_id=tenant_id)
    assert len(stages) == 2
    assert stages[0].name == "Applied"
