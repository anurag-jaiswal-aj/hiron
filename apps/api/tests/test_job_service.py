"""Unit test suite for JobService business logic, validations, permissions, and status transitions."""

import typing
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hiron.jobs.exceptions import (
    InsufficientJobPermissionsError,
    InvalidJobDataError,
    InvalidJobStatusTransitionError,
    JobNotFoundError,
)
from hiron.jobs.models import Job
from hiron.jobs.service import JobService


@pytest.fixture(autouse=True)
def force_qstash_engine(monkeypatch):
    monkeypatch.setenv("QSTASH_WEBHOOK_URL", "http://localhost:8000")
    from hiron.core.config import get_settings

    get_settings.cache_clear()


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


@pytest.fixture
def admin_user_id() -> uuid.UUID:
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def recruiter_user_id() -> uuid.UUID:
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def hm_user_id() -> uuid.UUID:
    return uuid.UUID("33333333-3333-3333-3333-333333333333")


@pytest.mark.asyncio
async def test_create_job_success_generates_default_pipeline_stages(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    recruiter_user_id: uuid.UUID,
) -> None:
    """Verify create_job persists job and auto-generates 6 default pipeline stages."""
    tenant_id = uuid.uuid4()
    created_by = recruiter_user_id

    mock_job_repo.create_job.side_effect = lambda _session, job: job
    mock_job_repo.create_pipeline_stages.side_effect = lambda _session, stages: stages

    call_order: list[str] = []

    async def mock_commit() -> None:
        call_order.append("commit")

    mock_session.commit.side_effect = mock_commit

    async def mock_publish(*_args: typing.Any, **_kwargs: typing.Any) -> str:
        call_order.append("publish")
        return "mock-task-id"

    service = JobService(job_repo=mock_job_repo)
    with patch(
        "hiron.core.qstash_client.QStashPublisher.publish",
        new_callable=AsyncMock,
        side_effect=mock_publish,
    ) as mock_publish_call:
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

    assert call_order == ["commit", "publish"], (
        "Job embedding task must be enqueued strictly AFTER commit"
    )
    mock_publish_call.assert_called_once()
    kwargs = mock_publish_call.call_args.kwargs
    assert kwargs["payload"]["job_id"] == str(job.id)


@pytest.mark.asyncio
async def test_create_job_insufficient_permissions_raises(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    hm_user_id: uuid.UUID,
) -> None:
    """Verify non-recruiter/non-admin cannot create jobs."""
    service = JobService(job_repo=mock_job_repo)
    with pytest.raises(InsufficientJobPermissionsError, match="create"):
        await service.create_job(
            session=mock_session,
            tenant_id=uuid.uuid4(),
            created_by=hm_user_id,
            current_user_role="hiring_manager",
            title="Title",
            description="Desc",
        )


@pytest.mark.asyncio
async def test_create_job_invalid_title_length_raises(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    admin_user_id: uuid.UUID,
) -> None:
    """Verify title exceeding 200 characters raises InvalidJobDataError."""
    service = JobService(job_repo=mock_job_repo)
    with pytest.raises(InvalidJobDataError, match="title"):
        await service.create_job(
            session=mock_session,
            tenant_id=uuid.uuid4(),
            created_by=admin_user_id,
            current_user_role="org_admin",
            title="A" * 201,
            description="Desc",
        )


@pytest.mark.asyncio
async def test_create_job_invalid_experience_range_raises(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    recruiter_user_id: uuid.UUID,
) -> None:
    """Verify max experience < min experience raises InvalidJobDataError."""
    service = JobService(job_repo=mock_job_repo)
    with pytest.raises(InvalidJobDataError, match="experience"):
        await service.create_job(
            session=mock_session,
            tenant_id=uuid.uuid4(),
            created_by=recruiter_user_id,
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
    recruiter_user_id: uuid.UUID,
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
        user_id=recruiter_user_id,
        current_user_role="recruiter",
    )

    assert updated.status == "open"
    mock_job_repo.update_job.assert_awaited_once()


@pytest.mark.asyncio
async def test_open_job_invalid_status_transition_raises(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    admin_user_id: uuid.UUID,
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
            user_id=admin_user_id,
            current_user_role="org_admin",
        )


@pytest.mark.asyncio
async def test_pause_job_success(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    recruiter_user_id: uuid.UUID,
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
        user_id=recruiter_user_id,
        current_user_role="recruiter",
    )

    assert updated.status == "paused"


@pytest.mark.asyncio
async def test_close_job_success(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    admin_user_id: uuid.UUID,
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
        user_id=admin_user_id,
        current_user_role="org_admin",
    )

    assert updated.status == "closed"


@pytest.mark.asyncio
async def test_archive_job_success(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    recruiter_user_id: uuid.UUID,
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
        user_id=recruiter_user_id,
        current_user_role="recruiter",
    )

    assert updated.status == "archived"
    assert updated.is_archived is True


@pytest.mark.asyncio
async def test_create_pipeline_stage_success(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    recruiter_user_id: uuid.UUID,
) -> None:
    """Verify custom pipeline stage creation."""
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_job = Job(id=job_id, tenant_id=tenant_id, title="Title", description="Desc")
    mock_job_repo.get_job_by_id.return_value = mock_job
    mock_job_repo.list_pipeline_stages.return_value = []
    mock_job_repo.create_pipeline_stage.side_effect = lambda _s, stage: stage

    service = JobService(job_repo=mock_job_repo)
    stage = await service.create_pipeline_stage(
        session=mock_session,
        job_id=job_id,
        tenant_id=tenant_id,
        user_id=recruiter_user_id,
        current_user_role="recruiter",
        name="Technical Challenge",
        position=3,
    )
    assert stage.name == "Technical Challenge"
    assert stage.position == 3


@pytest.mark.asyncio
async def test_delete_pipeline_stage_below_minimum_raises_conflict(
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    recruiter_user_id: uuid.UUID,
) -> None:
    """Verify deleting pipeline stage raises conflict if <= 2 stages remain."""
    from hiron.jobs.exceptions import PipelineStageConflictError
    from hiron.jobs.models import PipelineStage

    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    stage_id = uuid.uuid4()

    mock_job = Job(id=job_id, tenant_id=tenant_id, title="Title", description="Desc")
    mock_stage = PipelineStage(id=stage_id, tenant_id=tenant_id, job_id=job_id, name="Stage 1")
    mock_job_repo.get_job_by_id.return_value = mock_job
    mock_job_repo.get_pipeline_stage_by_id.return_value = mock_stage
    mock_job_repo.count_pipeline_stages.return_value = 2

    service = JobService(job_repo=mock_job_repo)
    with pytest.raises(PipelineStageConflictError, match="minimum 2 stages"):
        await service.delete_pipeline_stage(
            session=mock_session,
            job_id=job_id,
            stage_id=stage_id,
            tenant_id=tenant_id,
            user_id=recruiter_user_id,
            current_user_role="recruiter",
        )


@pytest.mark.asyncio
@patch("hiron.core.qstash_client.QStashPublisher.publish", new_callable=AsyncMock)
async def test_update_job_relevant_fields_enqueues_embedding_after_commit(
    mock_publish_call: MagicMock,
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    recruiter_user_id: uuid.UUID,
) -> None:
    """Verify relevant job updates enqueue embedding task strictly AFTER commit."""
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_job = MagicMock(id=job_id, title="Original")
    mock_job.experience_years_min = 3
    mock_job.experience_years_max = 5
    mock_job_repo.get_job_by_id.return_value = mock_job
    mock_job_repo.update_job.return_value = mock_job

    call_order: list[str] = []

    async def mock_commit() -> None:
        call_order.append("commit")

    mock_session.commit.side_effect = mock_commit

    async def mock_publish(*_args: typing.Any, **_kwargs: typing.Any) -> str:
        call_order.append("publish")
        return "mock-task-id"

    mock_publish_call.side_effect = mock_publish

    service = JobService(job_repo=mock_job_repo)
    await service.update_job(
        session=mock_session,
        job_id=job_id,
        tenant_id=tenant_id,
        user_id=recruiter_user_id,
        current_user_role="recruiter",
        description="New Description",  # Relevant field
    )

    assert call_order == ["commit", "publish"], (
        "Job embedding task must be enqueued strictly AFTER commit"
    )
    mock_publish_call.assert_called_once()
    kwargs = mock_publish_call.call_args.kwargs
    assert kwargs["payload"]["job_id"] == str(job_id)


@pytest.mark.asyncio
@patch("hiron.core.qstash_client.QStashPublisher.publish", new_callable=AsyncMock)
async def test_update_job_irrelevant_fields_does_not_enqueue_embedding(
    mock_publish_call: MagicMock,
    mock_session: AsyncMock,
    mock_job_repo: AsyncMock,
    recruiter_user_id: uuid.UUID,
) -> None:
    """Verify irrelevant job updates do NOT enqueue embedding task."""
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_job = MagicMock(id=job_id, title="Original")
    mock_job.experience_years_min = 3
    mock_job.experience_years_max = 5
    mock_job_repo.get_job_by_id.return_value = mock_job
    mock_job_repo.update_job.return_value = mock_job

    service = JobService(job_repo=mock_job_repo)
    await service.update_job(
        session=mock_session,
        job_id=job_id,
        tenant_id=tenant_id,
        user_id=recruiter_user_id,
        current_user_role="recruiter",
        department="New Department",  # Irrelevant field
    )

    mock_session.commit.assert_awaited_once()
    mock_publish_call.assert_not_called()
