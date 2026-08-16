"""Integration tests for end-to-end resume parsing pipeline, candidate auto-enrichment, and failure handling."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from apps.worker.src.pipeline import parse_resume_pipeline
from hiron.candidates.models import Candidate
from hiron.resumes.exceptions import ResumeNotFoundError, ResumeParseFailedError
from hiron.resumes.models import Resume, ResumeFile


@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.ResumeRepository")
@patch("apps.worker.src.pipeline.CandidateRepository")
@patch("hiron.storage.provider.LocalStorageProvider")
@patch("apps.worker.src.pipeline.ResumeParser")
@patch("apps.worker.src.pipeline.extract_text_from_file")
@patch("hiron.ai_usage.repository.AIUsageRepository.create_usage_log")
@patch("hiron.core.qstash_client.qstash_publisher.publish", new_callable=AsyncMock)
async def test_parse_resume_pipeline_success_and_candidate_enrichment(
    mock_publish: AsyncMock,
    mock_create_log: AsyncMock,
    mock_extract_text: MagicMock,
    mock_parser_cls: MagicMock,
    mock_storage_cls: MagicMock,
    mock_cand_repo_cls: MagicMock,
    mock_resume_repo_cls: MagicMock,
) -> None:
    """Verify parse_resume_pipeline updates resume status to parsed and auto-enriches candidate profile."""
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

    mock_resume_repo = mock_resume_repo_cls.return_value
    mock_resume_repo.get_resume_by_id = AsyncMock(return_value=mock_resume)
    mock_resume_repo.get_resume_file_by_resume_id = AsyncMock(return_value=mock_file)

    mock_cand_repo = mock_cand_repo_cls.return_value
    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=mock_candidate)

    mock_storage = mock_storage_cls.return_value
    mock_storage.download_file = AsyncMock(return_value=b"Jane Smith\njane.smith@example.com\nSenior Backend Engineer at Stripe\nSkills: Python, FastAPI, Docker, PostgreSQL")

    mock_extract_text.return_value = "Jane Smith\njane.smith@example.com\nSenior Backend Engineer at Stripe\nSkills: Python, FastAPI, Docker, PostgreSQL"

    parsed_data = {
        "full_name": "Jane Smith",
        "email": "jane.smith@example.com",
        "skills": ["Python", "FastAPI", "Docker", "PostgreSQL"],
    }
    mock_parser = mock_parser_cls.return_value
    mock_parser.model_version = "v1"
    mock_parser.parse.return_value = (parsed_data, 1.0, None)

    parsed_resume = Resume(
        id=resume_id,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        status="parsed",
        parse_confidence=1.0,
    )
    mock_resume_repo.update_resume_status = AsyncMock(return_value=parsed_resume)

    result = await parse_resume_pipeline(session, tenant_id, resume_id)

    assert result.status == "parsed"
    mock_resume_repo.update_resume_status.assert_called()
    mock_cand_repo.get_candidate_by_id.assert_called_once()
    assert mock_candidate.full_name == "Jane Smith"
    assert mock_candidate.email == "jane.smith@example.com"
    assert "Python" in mock_candidate.skills


@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.ResumeRepository")
async def test_parse_resume_pipeline_resume_not_found_raises_404(mock_resume_repo_cls: MagicMock) -> None:
    """Verify non-existent resume ID raises ResumeNotFoundError."""
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    mock_resume_repo = mock_resume_repo_cls.return_value
    mock_resume_repo.get_resume_by_id = AsyncMock(return_value=None)

    with pytest.raises(ResumeNotFoundError):
        await parse_resume_pipeline(session, tenant_id, resume_id)


@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.ResumeRepository")
async def test_parse_resume_pipeline_file_missing_raises_failed(mock_resume_repo_cls: MagicMock) -> None:
    """Verify missing file metadata sets resume status to failed and raises ResumeParseFailedError."""
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    mock_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=uuid.uuid4(), status="pending"
    )
    mock_resume_repo = mock_resume_repo_cls.return_value
    mock_resume_repo.get_resume_by_id = AsyncMock(return_value=mock_resume)
    mock_resume_repo.get_resume_file_by_resume_id = AsyncMock(return_value=None)
    mock_resume_repo.update_resume_status = AsyncMock(return_value=mock_resume)

    with pytest.raises(ResumeParseFailedError):
        await parse_resume_pipeline(session, tenant_id, resume_id)

    mock_resume_repo.update_resume_status.assert_called_once_with(
        session=session,
        resume=mock_resume,
        status="failed",
        parse_error=f"Resume file metadata missing for resume '{resume_id}'",
    )


@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.ResumeRepository")
@patch("apps.worker.src.pipeline.CandidateRepository")
@patch("hiron.storage.provider.LocalStorageProvider")
@patch("apps.worker.src.pipeline.ResumeParser")
@patch("apps.worker.src.pipeline.extract_text_from_file")
@patch("hiron.ai_usage.repository.AIUsageRepository.create_usage_log")
@patch("hiron.core.qstash_client.qstash_publisher.publish", new_callable=AsyncMock)
async def test_parse_resume_pipeline_telemetry_failure_isolation(
    mock_publish: AsyncMock,
    mock_create_log: AsyncMock,
    mock_extract_text: MagicMock,
    mock_parser_cls: MagicMock,
    mock_storage_cls: MagicMock,
    mock_cand_repo_cls: MagicMock,
    mock_resume_repo_cls: MagicMock,
) -> None:
    """Verify that a database failure while saving telemetry does NOT crash the parsing pipeline."""
    session = AsyncMock()
    session.begin_nested = MagicMock()
    session.begin_nested.return_value.__aenter__ = AsyncMock(return_value=None)
    session.begin_nested.return_value.__aexit__ = AsyncMock(return_value=None)

    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="pending"
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
        id=candidate_id, tenant_id=tenant_id, full_name="Candidate", email=None, skills=[]
    )

    mock_resume_repo = mock_resume_repo_cls.return_value
    mock_resume_repo.get_resume_by_id = AsyncMock(return_value=mock_resume)
    mock_resume_repo.get_resume_file_by_resume_id = AsyncMock(return_value=mock_file)

    mock_cand_repo = mock_cand_repo_cls.return_value
    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=mock_candidate)

    mock_storage = mock_storage_cls.return_value
    mock_storage.download_file = AsyncMock(return_value=b"Jane Smith\nSkills: Python")
    mock_extract_text.return_value = "Jane Smith\nSkills: Python"

    mock_parser = mock_parser_cls.return_value
    mock_parser.model_version = "v1"
    mock_parser.parse.return_value = ({"full_name": "Jane Smith", "skills": ["Python"]}, 1.0, None)

    # Make telemetry persistence fail!
    mock_create_log.side_effect = Exception("Simulated PostgreSQL Error during flush")

    parsed_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="parsed"
    )
    mock_resume_repo.update_resume_status = AsyncMock(return_value=parsed_resume)

    result = await parse_resume_pipeline(session, tenant_id, resume_id)

    # Parsing must still succeed despite the telemetry failure
    assert result.status == "parsed"
    mock_resume_repo.update_resume_status.assert_called()
