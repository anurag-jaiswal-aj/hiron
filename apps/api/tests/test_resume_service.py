"""Unit tests for ResumeService business logic, permissions, candidate binding, and status tracking."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hiron.candidates.models import Candidate
from hiron.common.exceptions import ValidationException
from hiron.jobs.models import Job
from hiron.resumes.exceptions import (
    FileTooLargeError,
    InsufficientResumePermissionsError,
    ResumeNotFoundError,
    UnsupportedFileTypeError,
)
from hiron.resumes.models import Resume, ResumeFile
from hiron.resumes.service import ResumeService


@pytest.fixture
def admin_user_id() -> uuid.UUID:
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.fixture
def recruiter_user_id() -> uuid.UUID:
    return uuid.UUID("22222222-2222-2222-2222-222222222222")


@pytest.fixture
def member_user_id() -> uuid.UUID:
    return uuid.UUID("44444444-4444-4444-4444-444444444444")


@pytest.mark.asyncio
async def test_upload_resume_unauthorized_role_raises_403(member_user_id: uuid.UUID) -> None:
    """Verify member role raises InsufficientResumePermissionsError."""
    service = ResumeService(storage_provider=AsyncMock())
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    with pytest.raises(InsufficientResumePermissionsError):
        await service.upload_resume(
            session=session,
            tenant_id=tenant_id,
            user_id=member_user_id,
            user_role="member",
            filename="resume.pdf",
            content_type="application/pdf",
            file_bytes=b"dummy",
        )


@pytest.mark.asyncio
async def test_upload_resume_file_too_large_raises_413(recruiter_user_id: uuid.UUID) -> None:
    """Verify file > 10 MB raises FileTooLargeError."""
    service = ResumeService(storage_provider=AsyncMock())
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    large_bytes = b"x" * (10 * 1024 * 1024 + 1)

    with pytest.raises(FileTooLargeError):
        await service.upload_resume(
            session=session,
            tenant_id=tenant_id,
            user_id=recruiter_user_id,
            user_role="recruiter",
            filename="resume.pdf",
            content_type="application/pdf",
            file_bytes=large_bytes,
        )


@pytest.mark.asyncio
async def test_upload_resume_unsupported_type_raises_415(recruiter_user_id: uuid.UUID) -> None:
    """Verify unsupported type raises UnsupportedFileTypeError."""
    service = ResumeService(storage_provider=AsyncMock())
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    with pytest.raises(UnsupportedFileTypeError):
        await service.upload_resume(
            session=session,
            tenant_id=tenant_id,
            user_id=recruiter_user_id,
            user_role="recruiter",
            filename="photo.jpg",
            content_type="image/jpeg",
            file_bytes=b"dummy",
        )


@pytest.mark.asyncio
async def test_upload_resume_placeholder_candidate_creation(recruiter_user_id: uuid.UUID) -> None:
    """Verify upload creates a placeholder candidate when candidate_id is omitted."""
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

    mock_candidate = Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="John Doe", source="upload"
    )
    candidate_repo.create_candidate.return_value = mock_candidate

    mock_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="parsed"
    )
    mock_file = ResumeFile(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        resume_id=resume_id,
        s3_bucket="hiron-resumes",
        s3_key=f"{tenant_id}/john_doe_resume.txt",
        original_filename="john_doe_resume.txt",
        content_type="text/plain",
        file_size_bytes=100,
        checksum_sha256="abc123sha",
    )
    storage_provider.download_file.return_value = b"John Doe\njohn@example.com\nPython, FastAPI"
    resume_repo.create_resume.return_value = mock_resume
    resume_repo.create_resume_file.return_value = mock_file
    resume_repo.get_resume_file_by_resume_id.return_value = mock_file
    resume_repo.get_resume_by_id.return_value = mock_resume
    resume_repo.update_resume_status.return_value = mock_resume
    candidate_repo.get_candidate_by_id.return_value = mock_candidate

    response = await service.upload_resume(
        session=session,
        tenant_id=tenant_id,
        user_id=recruiter_user_id,
        user_role="recruiter",
        filename="john_doe_resume.pdf",
        content_type="application/pdf",
        file_bytes=b"%PDF-1.4 sample text",
    )

    assert response.resume_id == resume_id
    assert response.candidate_id == candidate_id
    assert response.status in ("parsed", "pending")

    candidate_repo.create_candidate.assert_called_once()
    resume_repo.create_resume.assert_called_once()
    storage_provider.upload_file.assert_called_once()


@pytest.mark.asyncio
async def test_upload_resume_existing_candidate_and_job_assignment(admin_user_id: uuid.UUID) -> None:
    """Verify upload binds to existing candidate and associates with job when provided."""
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
    job_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    resume_repo.find_file_by_checksum.return_value = None
    candidate_repo.get_candidate_by_id.return_value = Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="Sarah Connor"
    )
    job_repo.get_job_by_id.return_value = Job(
        id=job_id, tenant_id=tenant_id, title="Backend Engineer"
    )

    mock_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="pending"
    )
    resume_repo.create_resume.return_value = mock_resume

    response = await service.upload_resume(
        session=session,
        tenant_id=tenant_id,
        user_id=admin_user_id,
        user_role="org_admin",
        filename="sarah_resume.pdf",
        content_type="application/pdf",
        file_bytes=b"%PDF-1.4 test sarah",
        candidate_id=candidate_id,
        job_id=job_id,
    )

    assert response.resume_id == resume_id
    candidate_repo.create_candidate.assert_not_called()
    candidate_service.add_candidate_to_job.assert_called_once()


@pytest.mark.asyncio
async def test_upload_resume_idempotent_duplicate(recruiter_user_id: uuid.UUID) -> None:
    """Verify duplicate file content upload returns existing upload response."""
    resume_repo = AsyncMock()
    service = ResumeService(resume_repository=resume_repo, storage_provider=AsyncMock())

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_file = MagicMock(spec=ResumeFile)
    mock_file.resume_id = resume_id
    mock_file.resume = MagicMock(spec=Resume)
    mock_file.resume.candidate_id = candidate_id
    mock_file.resume.status = "pending"

    resume_repo.find_file_by_checksum.return_value = mock_file

    response = await service.upload_resume(
        session=session,
        tenant_id=tenant_id,
        user_id=recruiter_user_id,
        user_role="recruiter",
        filename="duplicate.pdf",
        content_type="application/pdf",
        file_bytes=b"%PDF-1.4 duplicate text",
    )

    assert response.resume_id == resume_id
    assert response.candidate_id == candidate_id


@pytest.mark.asyncio
async def test_bulk_upload_resumes_rejections(recruiter_user_id: uuid.UUID) -> None:
    """Verify bulk upload filters out files > 10 MB or unsupported file types into rejections."""
    resume_repo = AsyncMock()
    candidate_repo = AsyncMock()
    service = ResumeService(resume_repository=resume_repo, candidate_repository=candidate_repo, storage_provider=AsyncMock())

    session = AsyncMock()
    tenant_id = uuid.uuid4()

    resume_repo.find_file_by_checksum.return_value = None
    candidate_repo.create_candidate.return_value = Candidate(
        id=uuid.uuid4(), tenant_id=tenant_id, full_name="Valid Candidate"
    )
    resume_repo.create_resume.return_value = Resume(
        id=uuid.uuid4(), tenant_id=tenant_id, candidate_id=uuid.uuid4(), status="pending"
    )

    files = [
        ("valid.pdf", "application/pdf", b"%PDF-1.4 valid"),
        ("huge.pdf", "application/pdf", b"x" * (10 * 1024 * 1024 + 10)),
        ("photo.png", "image/png", b"png bytes"),
    ]

    response = await service.bulk_upload_resumes(
        session=session,
        tenant_id=tenant_id,
        user_id=recruiter_user_id,
        user_role="recruiter",
        files=files,
    )

    assert response.total_files == 3
    assert response.accepted == 1
    assert response.rejected == 2
    assert len(response.rejections) == 2


@pytest.mark.asyncio
async def test_get_resume_status_not_found_raises_404() -> None:
    """Verify non-existent resume ID raises ResumeNotFoundError."""
    resume_repo = AsyncMock()
    service = ResumeService(resume_repository=resume_repo, storage_provider=AsyncMock())

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    resume_repo.get_resume_by_id.return_value = None

    with pytest.raises(ResumeNotFoundError):
        await service.get_resume_status(session, tenant_id, resume_id)


@pytest.mark.asyncio
async def test_retry_parse_success(recruiter_user_id: uuid.UUID) -> None:
    """Verify retrying a failed resume resets status to pending."""
    resume_repo = AsyncMock()
    candidate_repo = AsyncMock()
    service = ResumeService(resume_repository=resume_repo, candidate_repository=candidate_repo, storage_provider=AsyncMock())

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    failed_resume = Resume(
        id=resume_id,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        status="failed",
        parse_error="Timeout",
    )
    parsed_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="parsed"
    )
    mock_file = ResumeFile(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        resume_id=resume_id,
        s3_bucket="hiron-resumes",
        s3_key=f"{tenant_id}/sample.txt",
        original_filename="sample.txt",
        content_type="text/plain",
        file_size_bytes=100,
        checksum_sha256="abc123sha",
    )

    resume_repo.get_resume_by_id.return_value = failed_resume
    resume_repo.get_resume_file_by_resume_id.return_value = mock_file
    resume_repo.update_resume_status.return_value = parsed_resume
    candidate_repo.get_candidate_by_id.return_value = None

    with patch("hiron.core.config.get_settings") as mock_settings:
        mock_settings.return_value.worker_url = "http://test"
        with patch("hiron.core.qstash_client.QStashPublisher.publish") as mock_publish:
            mock_publish.return_value = "task-retry-123"
            response = await service.retry_parse(
                session=session,
                tenant_id=tenant_id,
                user_id=recruiter_user_id,
                user_role="recruiter",
                resume_id=resume_id,
            )

        assert response.status == "pending"
        assert response.task_id == "task-retry-123"
        assert resume_repo.update_resume_status.called


@pytest.mark.asyncio
async def test_retry_parse_not_failed_status_raises_validation_exception(recruiter_user_id: uuid.UUID) -> None:
    """Verify retrying a non-failed resume raises ValidationException."""
    resume_repo = AsyncMock()
    service = ResumeService(resume_repository=resume_repo, storage_provider=AsyncMock())

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    parsed_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=uuid.uuid4(), status="parsed"
    )
    resume_repo.get_resume_by_id.return_value = parsed_resume

    with pytest.raises(ValidationException):
        await service.retry_parse(
            session=session,
            tenant_id=tenant_id,
            user_id=recruiter_user_id,
            user_role="recruiter",
            resume_id=resume_id,
        )


@pytest.mark.asyncio
async def test_upload_resume_qstash_publish_failure_raises_503(recruiter_user_id: uuid.UUID) -> None:
    """Verify that a QStash publish exception results in a failed resume status and raises a 503 error."""
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
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    resume_repo.find_file_by_checksum.return_value = None
    mock_candidate = Candidate(id=candidate_id, tenant_id=tenant_id, full_name="John Doe", source="upload")
    candidate_repo.create_candidate.return_value = mock_candidate
    mock_resume = Resume(id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="pending")
    resume_repo.create_resume.return_value = mock_resume

    with patch("hiron.core.config.get_settings") as mock_settings:
        mock_settings.return_value.worker_url = "http://test"
        with patch("hiron.core.qstash_client.QStashPublisher.publish") as mock_publish:
            mock_publish.side_effect = Exception("Simulated QStash network failure")

            from hiron.common.exceptions import HironException
            with pytest.raises(HironException) as exc_info:
                await service.upload_resume(
                    session=session,
                    tenant_id=tenant_id,
                    user_id=recruiter_user_id,
                    user_role="recruiter",
                    filename="resume.pdf",
                    content_type="application/pdf",
                    file_bytes=b"sample",
                )

        assert exc_info.value.status_code == 503
        assert exc_info.value.code == "QUEUE_ERROR"

        resume_repo.update_resume_status.assert_called_once_with(
            session=session,
            resume=mock_resume,
            status="failed",
            parse_error="Queue error: Simulated QStash network failure"
        )
        assert session.commit.call_count == 2
