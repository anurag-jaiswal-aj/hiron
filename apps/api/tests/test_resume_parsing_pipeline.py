"""Integration tests for end-to-end resume parsing pipeline, candidate auto-enrichment, and failure handling."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest

from hiron.candidates.models import Candidate
from hiron.resumes.exceptions import ResumeNotFoundError, ResumeParseFailedError
from hiron.resumes.models import Resume, ResumeFile
from hiron.resumes.service import ResumeService


@pytest.mark.asyncio
@patch("hiron.resumes.parser.get_nlp")
@patch("hiron.ai_usage.repository.AIUsageRepository.create_usage_log")
async def test_parse_resume_pipeline_success_and_candidate_enrichment(
    mock_create_log: AsyncMock, mock_get_nlp: AsyncMock
) -> None:
    """Verify parse_resume_pipeline updates resume status to parsed and auto-enriches candidate profile."""
    resume_repo = AsyncMock()
    candidate_repo = AsyncMock()
    storage_provider = AsyncMock()

    service = ResumeService(
        resume_repository=resume_repo,
        candidate_repository=candidate_repo,
        storage_provider=storage_provider,
    )

    from unittest.mock import MagicMock
    session = AsyncMock()
    session.begin_nested = MagicMock()
    session.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_resume = Resume(
        id=resume_id,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        status="pending",
    )
    mock_file = ResumeFile(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        resume_id=resume_id,
        s3_bucket="hiron-resumes",
        s3_key=f"{tenant_id}/{resume_id}/original.txt",
        original_filename="jane_smith_resume.txt",
        content_type="text/plain",
        file_size_bytes=100,
        checksum_sha256="abc123sha",
    )
    mock_candidate = Candidate(
        id=candidate_id,
        tenant_id=tenant_id,
        full_name="Placeholder Candidate",
        email=None,
        skills=[],
    )

    resume_repo.get_resume_by_id.return_value = mock_resume
    resume_repo.get_resume_file_by_resume_id.return_value = mock_file
    candidate_repo.get_candidate_by_id.return_value = mock_candidate

    from unittest.mock import MagicMock
    mock_doc = MagicMock()
    mock_doc.ents = []
    mock_nlp = MagicMock(return_value=mock_doc)
    mock_get_nlp.return_value = mock_nlp

    raw_resume_bytes = b"Jane Smith\njane.smith@example.com\nSenior Backend Engineer at Stripe\nSkills: Python, FastAPI, Docker, PostgreSQL"
    storage_provider.download_file.return_value = raw_resume_bytes

    parsed_resume = Resume(
        id=resume_id,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        status="parsed",
        parse_confidence=1.0,
    )
    resume_repo.update_resume_status.return_value = parsed_resume

    result = await service.parse_resume_pipeline(session, tenant_id, resume_id)

    assert result.status == "parsed"
    resume_repo.update_resume_status.assert_called()
    update_kwargs = resume_repo.update_resume_status.call_args.kwargs
    assert update_kwargs["raw_text"] == raw_resume_bytes.decode("utf-8")
    assert "raw_text_hash" in update_kwargs

    candidate_repo.get_candidate_by_id.assert_called_once()
    assert mock_candidate.full_name == "Jane Smith"
    assert mock_candidate.email == "jane.smith@example.com"
    assert "Python" in mock_candidate.skills

    mock_create_log.assert_called_once()
    log_kwargs = mock_create_log.call_args.kwargs
    assert log_kwargs["operation"] == "resume_parsing"
    assert log_kwargs["status"] == "success"
    assert log_kwargs["tenant_id"] == tenant_id


@pytest.mark.asyncio
async def test_parse_resume_pipeline_resume_not_found_raises_404() -> None:
    """Verify non-existent resume ID raises ResumeNotFoundError."""
    resume_repo = AsyncMock()
    service = ResumeService(resume_repository=resume_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    resume_repo.get_resume_by_id.return_value = None

    with pytest.raises(ResumeNotFoundError):
        await service.parse_resume_pipeline(session, tenant_id, resume_id)


@pytest.mark.asyncio
async def test_parse_resume_pipeline_file_missing_raises_failed() -> None:
    """Verify missing file metadata sets resume status to failed and raises ResumeParseFailedError."""
    resume_repo = AsyncMock()
    service = ResumeService(resume_repository=resume_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    mock_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=uuid.uuid4(), status="pending"
    )
    resume_repo.get_resume_by_id.return_value = mock_resume
    resume_repo.get_resume_file_by_resume_id.return_value = None

    with pytest.raises(ResumeParseFailedError):
        await service.parse_resume_pipeline(session, tenant_id, resume_id)

    resume_repo.update_resume_status.assert_called_once_with(
        session=session,
        resume=mock_resume,
        status="failed",
        parse_error=f"Resume file metadata missing for resume '{resume_id}'",
    )


@pytest.mark.asyncio
@patch("hiron.resumes.parser.get_nlp")
@patch("hiron.ai_usage.repository.AIUsageRepository.create_usage_log")
async def test_parse_resume_pipeline_telemetry_failure_isolation(
    mock_create_log: AsyncMock, mock_get_nlp: AsyncMock
) -> None:
    """Verify that a database failure while saving telemetry does NOT crash the parsing pipeline."""
    resume_repo = AsyncMock()
    candidate_repo = AsyncMock()
    storage_provider = AsyncMock()
    service = ResumeService(
        resume_repository=resume_repo,
        candidate_repository=candidate_repo,
        storage_provider=storage_provider,
    )

    from unittest.mock import MagicMock
    session = AsyncMock()
    session.begin_nested = MagicMock()
    session.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    mock_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=uuid.uuid4(), status="pending"
    )
    mock_file = ResumeFile(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        resume_id=resume_id,
        s3_bucket="hiron-resumes",
        s3_key=f"{tenant_id}/{resume_id}/original.txt",
        original_filename="jane_smith_resume.txt",
        content_type="text/plain",
        file_size_bytes=100,
        checksum_sha256="abc123sha",
    )
    resume_repo.get_resume_by_id.return_value = mock_resume
    resume_repo.get_resume_file_by_resume_id.return_value = mock_file
    candidate_repo.get_candidate_by_id.return_value = Candidate(
        id=uuid.uuid4(), tenant_id=tenant_id, full_name="Candidate", email=None, skills=[]
    )

    from unittest.mock import MagicMock
    mock_nlp = MagicMock(return_value=MagicMock(ents=[]))
    mock_get_nlp.return_value = mock_nlp
    storage_provider.download_file.return_value = b"Jane Smith\nSkills: Python"

    # Make telemetry persistence fail!
    mock_create_log.side_effect = Exception("Simulated PostgreSQL Error during flush")

    parsed_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=uuid.uuid4(), status="parsed"
    )
    resume_repo.update_resume_status.return_value = parsed_resume

    result = await service.parse_resume_pipeline(session, tenant_id, resume_id)

    # Parsing must still succeed despite the telemetry failure
    assert result.status == "parsed"
    resume_repo.update_resume_status.assert_called()
    mock_create_log.assert_called_once()
