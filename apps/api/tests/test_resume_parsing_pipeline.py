"""Integration tests for end-to-end resume parsing pipeline, candidate auto-enrichment, and failure handling."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.candidates.models import Candidate
from hiron.resumes.exceptions import ResumeNotFoundError, ResumeParseFailedError
from hiron.resumes.models import Resume, ResumeFile
from hiron.resumes.service import ResumeService


@pytest.mark.asyncio
async def test_parse_resume_pipeline_success_and_candidate_enrichment() -> None:
    """Verify parse_resume_pipeline updates resume status to parsed and auto-enriches candidate profile."""
    resume_repo = AsyncMock()
    candidate_repo = AsyncMock()
    storage_provider = AsyncMock()

    service = ResumeService(
        resume_repository=resume_repo,
        candidate_repository=candidate_repo,
        storage_provider=storage_provider,
    )

    session = AsyncMock()
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
    candidate_repo.get_candidate_by_id.assert_called_once()
    assert mock_candidate.full_name == "Jane Smith"
    assert mock_candidate.email == "jane.smith@example.com"
    assert "Python" in mock_candidate.skills


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
