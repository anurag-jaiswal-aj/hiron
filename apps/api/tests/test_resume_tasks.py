"""Unit tests for Celery resume background tasks and async transaction handling per Requirement G."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hiron.resumes.models import Resume, ResumeFile
from hiron.resumes.service import ResumeService
from hiron.resumes.tasks import parse_resume


@pytest.mark.asyncio
async def test_upload_commits_metadata_before_enqueue_and_returns_celery_task_id() -> None:
    """Verify upload_resume commits metadata BEFORE enqueueing Celery task and returns real Celery task ID."""
    resume_repo = AsyncMock()
    candidate_repo = AsyncMock()
    job_repo = AsyncMock()
    candidate_service = AsyncMock()
    storage_provider = AsyncMock()

    service = ResumeService(
        resume_repository=resume_repo,
        candidate_repository=candidate_repo,
        job_repository=job_repo,
        candidate_service=candidate_service,
        storage_provider=storage_provider,
    )

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    resume_repo.find_file_by_checksum.return_value = None
    candidate_repo.create_candidate.return_value = MagicMock(id=candidate_id)
    resume_repo.create_resume.return_value = MagicMock(id=resume_id)
    resume_repo.create_resume_file.return_value = MagicMock(id=uuid.uuid4())

    call_order: list[str] = []

    async def mock_commit() -> None:
        call_order.append("commit")

    session.commit = AsyncMock(side_effect=mock_commit)

    mock_celery_task = MagicMock()
    mock_celery_task.id = "celery-task-12345"

    def mock_delay(t_id: str, r_id: str) -> MagicMock:
        call_order.append("delay")
        return mock_celery_task

    with patch("hiron.resumes.tasks.parse_resume.delay", side_effect=mock_delay) as mock_delay_patch:
        response = await service.upload_resume(
            session=session,
            tenant_id=tenant_id,
            user_role="recruiter",
            filename="john_doe.pdf",
            content_type="application/pdf",
            file_bytes=b"%PDF-1.4 test bytes",
        )

        # 1. Explicitly verify call sequence: session.commit() MUST precede parse_resume.delay(...)
        assert call_order == ["commit", "delay"], f"Expected ['commit', 'delay'], got {call_order}"

        # 2. Assert Celery delay arguments
        mock_delay_patch.assert_called_once_with(str(tenant_id), str(resume_id))

        # 3. Assert real Celery task ID and pending status are returned
        assert response.task_id == "celery-task-12345"
        assert response.status == "pending"


@pytest.mark.asyncio
async def test_retry_parse_enqueues_celery_task() -> None:
    """Verify retry_parse updates status to pending, commits, and enqueues Celery task."""
    resume_repo = AsyncMock()
    service = ResumeService(resume_repository=resume_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    failed_resume = Resume(
        id=resume_id,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        status="failed",
        parse_error="Previous error",
    )
    resume_repo.get_resume_by_id.return_value = failed_resume

    mock_celery_task = MagicMock()
    mock_celery_task.id = "celery-retry-task-999"

    with patch("hiron.resumes.tasks.parse_resume.delay", return_value=mock_celery_task) as mock_delay:
        response = await service.retry_parse(
            session=session,
            tenant_id=tenant_id,
            user_role="recruiter",
            resume_id=resume_id,
        )

        resume_repo.update_resume_status.assert_called_once_with(
            session=session,
            resume=failed_resume,
            status="pending",
            parse_error="",
        )
        session.commit.assert_called_once()
        mock_delay.assert_called_once_with(str(tenant_id), str(resume_id))
        assert response.task_id == "celery-retry-task-999"
        assert response.status == "pending"


def test_celery_task_commits_successful_parse() -> None:
    """Verify Celery parse_resume task commits on successful parse pipeline execution."""
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    mock_session = AsyncMock()

    with (
        patch("hiron.resumes.tasks.AsyncSessionLocal", return_value=mock_session),
        patch.object(ResumeService, "parse_resume_pipeline", new_callable=AsyncMock) as mock_pipeline,
    ):
        mock_session.__aenter__.return_value = mock_session

        result = parse_resume(str(tenant_id), str(resume_id))

        mock_pipeline.assert_awaited_once_with(
            session=mock_session,
            tenant_id=tenant_id,
            resume_id=resume_id,
        )
        mock_session.commit.assert_awaited_once()
        assert result == {"status": "success", "resume_id": str(resume_id)}


def test_celery_task_rolls_back_and_persists_failed_status_on_failure() -> None:
    """Verify Celery task rolls back main session and persists failed status in fresh session on error."""
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    main_session = AsyncMock()
    fail_session = AsyncMock()

    mock_repo = AsyncMock()
    mock_resume = Resume(id=resume_id, tenant_id=tenant_id, status="pending")
    mock_repo.get_resume_by_id.return_value = mock_resume

    with (
        patch("hiron.resumes.tasks.AsyncSessionLocal", side_effect=[main_session, fail_session]),
        patch("hiron.resumes.tasks.ResumeRepository", return_value=mock_repo),
        patch.object(ResumeService, "parse_resume_pipeline", side_effect=ValueError("Pipeline crashed")),
    ):
        main_session.__aenter__.return_value = main_session
        fail_session.__aenter__.return_value = fail_session

        with pytest.raises(ValueError, match="Pipeline crashed"):
            parse_resume(str(tenant_id), str(resume_id))

        main_session.rollback.assert_awaited_once()
        mock_repo.get_resume_by_id.assert_awaited_once_with(
            session=fail_session,
            tenant_id=tenant_id,
            resume_id=resume_id,
        )
        mock_repo.update_resume_status.assert_awaited_once_with(
            session=fail_session,
            resume=mock_resume,
            status="failed",
            parse_error="Pipeline crashed",
        )
        fail_session.commit.assert_awaited_once()
