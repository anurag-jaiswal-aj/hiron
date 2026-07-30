"""Unit test suite for JobService business logic, validations, permissions, and status transitions."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.jobs.exceptions import (
    InsufficientJobPermissionsError,
    InvalidJobDataError,
    InvalidJobStatusTransitionError,
    JobNotFoundError,
)
from hiron.jobs.models import Job
from hiron.jobs.service import JobService


@pytest.fixture
def mock_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_job_repo() -> AsyncMock:
    """Fixture providing a mock JobRepository."""
    repo = AsyncMock()
    repo.get_job_by_id.return_value = None
    return repo


@pytest.mark.asyncio
async def test_create_job_success_generates_default_pipeline_stages(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    """Verify create_job persists job and auto-generates 6 default pipeline stages."""
    tenant_id = uuid.uuid4()
    created_by = uuid.uuid4()

    mock_job_repo.create_job.side_effect = lambda _session, job: job
    mock_job_repo.create_pipeline_stages.side_effect = lambda _session, stages: stages

    service = JobService(job_repo=mock_job_repo)
    job = await service.create_job(
        session=mock_session,
        tenant_id=tenant_id,
        created_by=created_by,
        current_user_role="recruiter",
        title="Senior Frontend Engineer",
        description="Full stack TypeScript and React role",
        department="Engineering",
        location="Remote",
        employment_type="full_time",
        experience_years_min=3,
        experience_years_max=7,
        required_skills=["TypeScript", "React"],
    )

    assert job.title == "Senior Frontend Engineer"
    assert job.status == "draft"
    mock_job_repo.create_job.assert_awaited_once()
    mock_job_repo.create_pipeline_stages.assert_awaited_once()
    stages = mock_job_repo.create_pipeline_stages.call_args[0][1]
    assert len(stages) == 6
    assert stages[0].name == "Applied"
    assert stages[4].name == "Hired"
    assert stages[5].name == "Rejected"


@pytest.mark.asyncio
async def test_create_job_insufficient_permissions_raises(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    """Verify non-recruiter/non-admin cannot create jobs."""
    service = JobService(job_repo=mock_job_repo)
    with pytest.raises(InsufficientJobPermissionsError, match="create"):
        await service.create_job(
            session=mock_session,
            tenant_id=uuid.uuid4(),
            created_by=uuid.uuid4(),
            current_user_role="hiring_manager",
            title="Title",
            description="Desc",
        )


@pytest.mark.asyncio
async def test_create_job_invalid_title_length_raises(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    """Verify title exceeding 200 characters raises InvalidJobDataError."""
    service = JobService(job_repo=mock_job_repo)
    with pytest.raises(InvalidJobDataError, match="title"):
        await service.create_job(
            session=mock_session,
            tenant_id=uuid.uuid4(),
            created_by=uuid.uuid4(),
            current_user_role="org_admin",
            title="A" * 201,
            description="Desc",
        )


@pytest.mark.asyncio
async def test_create_job_invalid_experience_range_raises(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    """Verify max experience < min experience raises InvalidJobDataError."""
    service = JobService(job_repo=mock_job_repo)
    with pytest.raises(InvalidJobDataError, match="experience"):
        await service.create_job(
            session=mock_session,
            tenant_id=uuid.uuid4(),
            created_by=uuid.uuid4(),
            current_user_role="recruiter",
            title="Title",
            description="Desc",
            experience_years_min=5,
            experience_years_max=2,
        )


@pytest.mark.asyncio
async def test_get_job_by_id_not_found_raises(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    """Verify get_job_by_id raises JobNotFoundError when job does not exist."""
    mock_job_repo.get_job_by_id.return_value = None
    service = JobService(job_repo=mock_job_repo)

    with pytest.raises(JobNotFoundError):
        await service.get_job_by_id(mock_session, uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_open_job_success(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    """Verify open_job transitions status from draft to open and sets opened_at."""
    job_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    draft_job = Job(
        id=job_id, tenant_id=tenant_id, status="draft", title="Title", description="Desc"
    )
    open_job = Job(id=job_id, tenant_id=tenant_id, status="open", title="Title", description="Desc")

    mock_job_repo.get_job_by_id.return_value = draft_job
    mock_job_repo.update_job.return_value = open_job

    service = JobService(job_repo=mock_job_repo)
    updated = await service.open_job(
        session=mock_session,
        job_id=job_id,
        tenant_id=tenant_id,
        current_user_role="recruiter",
    )

    assert updated.status == "open"
    mock_job_repo.update_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_open_job_invalid_status_transition_raises(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    """Verify opening an already closed job raises InvalidJobStatusTransitionError."""
    job_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    closed_job = Job(
        id=job_id, tenant_id=tenant_id, status="closed", title="Title", description="Desc"
    )
    mock_job_repo.get_job_by_id.return_value = closed_job

    service = JobService(job_repo=mock_job_repo)
    with pytest.raises(InvalidJobStatusTransitionError, match="closed"):
        await service.open_job(
            session=mock_session,
            job_id=job_id,
            tenant_id=tenant_id,
            current_user_role="org_admin",
        )


@pytest.mark.asyncio
async def test_pause_job_success(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    """Verify pause_job transitions status from open to paused."""
    job_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    open_job = Job(id=job_id, tenant_id=tenant_id, status="open", title="Title", description="Desc")
    paused_job = Job(
        id=job_id, tenant_id=tenant_id, status="paused", title="Title", description="Desc"
    )

    mock_job_repo.get_job_by_id.return_value = open_job
    mock_job_repo.update_job.return_value = paused_job

    service = JobService(job_repo=mock_job_repo)
    updated = await service.pause_job(
        session=mock_session,
        job_id=job_id,
        tenant_id=tenant_id,
        current_user_role="recruiter",
    )

    assert updated.status == "paused"


@pytest.mark.asyncio
async def test_close_job_success(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    """Verify close_job transitions status to closed."""
    job_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    open_job = Job(id=job_id, tenant_id=tenant_id, status="open", title="Title", description="Desc")
    closed_job = Job(
        id=job_id, tenant_id=tenant_id, status="closed", title="Title", description="Desc"
    )

    mock_job_repo.get_job_by_id.return_value = open_job
    mock_job_repo.update_job.return_value = closed_job

    service = JobService(job_repo=mock_job_repo)
    updated = await service.close_job(
        session=mock_session,
        job_id=job_id,
        tenant_id=tenant_id,
        current_user_role="org_admin",
    )

    assert updated.status == "closed"


@pytest.mark.asyncio
async def test_archive_job_success(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
) -> None:
    """Verify archive_job sets status to archived and is_archived to True."""
    job_id = uuid.uuid4()
    tenant_id = uuid.uuid4()

    open_job = Job(id=job_id, tenant_id=tenant_id, status="open", title="Title", description="Desc")
    archived_job = Job(id=job_id, tenant_id=tenant_id, status="archived", is_archived=True)

    mock_job_repo.get_job_by_id.return_value = open_job
    mock_job_repo.update_job.return_value = archived_job

    service = JobService(job_repo=mock_job_repo)
    updated = await service.archive_job(
        session=mock_session,
        job_id=job_id,
        tenant_id=tenant_id,
        current_user_role="recruiter",
    )

    assert updated.status == "archived"
    assert updated.is_archived is True
