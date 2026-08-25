"""Tests to verify large resume text extraction limits and truncation behavior."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apps.worker.src.extractor import (
    MAX_RESUME_TEXT_CHARS,
    extract_text_from_file,
    extract_text_from_txt,
)
from apps.worker.src.pipeline import parse_resume_pipeline

from hiron.candidates.models import Candidate
from hiron.resumes.models import Resume, ResumeFile


def test_extractor_below_limit_remains_unchanged() -> None:
    """Verify normal resume below limit is not truncated."""
    text = "A" * 1000
    extracted, is_truncated = extract_text_from_txt(text.encode("utf-8"), max_chars=30_000)
    assert len(extracted) == 1000
    assert not is_truncated
    assert extracted == text


def test_extractor_exactly_at_limit_remains_unchanged() -> None:
    """Verify resume exactly at the limit is not truncated."""
    text = "A" * 30_000
    extracted, is_truncated = extract_text_from_txt(text.encode("utf-8"), max_chars=30_000)
    assert len(extracted) == 30_000
    assert not is_truncated
    assert extracted == text


def test_extractor_above_limit_truncates() -> None:
    """Verify resume exceeding limit is truncated and flag is set."""
    text = "A" * 50_000
    extracted, is_truncated = extract_text_from_txt(text.encode("utf-8"), max_chars=30_000)
    assert len(extracted) == 30_000
    assert is_truncated


def test_extract_text_from_file_large_text() -> None:
    """Verify very large synthetic text input does not construct unbounded text."""
    text = "B" * 60_000
    extracted, is_truncated = extract_text_from_file(text.encode("utf-8"), "text/plain", "resume.txt")
    assert len(extracted) <= MAX_RESUME_TEXT_CHARS
    assert is_truncated


@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.ResumeRepository")
@patch("apps.worker.src.pipeline.CandidateRepository")
@patch("hiron.storage.provider.LocalStorageProvider")
@patch("apps.worker.src.pipeline.GeminiResumeParser")
@patch("apps.worker.src.pipeline.extract_text_from_file")
@patch("hiron.ai_usage.repository.AIUsageRepository.create_usage_log")
@patch("hiron.core.qstash_client.qstash_publisher.publish", new_callable=AsyncMock)
async def test_pipeline_gemini_integration_receives_bounded_text(
    mock_publish: AsyncMock,
    mock_create_log: AsyncMock,
    mock_extract_text: MagicMock,
    mock_parser_cls: MagicMock,
    mock_storage_cls: MagicMock,
    mock_cand_repo_cls: MagicMock,
    mock_resume_repo_cls: MagicMock,
) -> None:
    """Verify pipeline integrates with extractor correctly and passes bounded text to Gemini."""
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
        original_filename="large_resume.txt",
        content_type="text/plain",
        file_size_bytes=60_000,
        checksum_sha256="abc123sha",
    )
    mock_candidate = Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="Placeholder Candidate", email=None, skills=[]
    )

    mock_resume_repo = mock_resume_repo_cls.return_value
    mock_resume_repo.get_resume_by_id = AsyncMock(return_value=mock_resume)
    mock_resume_repo.get_resume_file_by_resume_id = AsyncMock(return_value=mock_file)

    mock_cand_repo = mock_cand_repo_cls.return_value
    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=mock_candidate)

    mock_storage = mock_storage_cls.return_value
    mock_storage.download_file = AsyncMock(return_value=b"A" * 60_000)

    # Return exactly the limit with truncation flag=True
    mock_extract_text.return_value = ("A" * MAX_RESUME_TEXT_CHARS, True)

    mock_parser = mock_parser_cls.return_value
    mock_parser.model_version = "v1"
    mock_parser.parse_async = AsyncMock(return_value=({"full_name": "Truncated User"}, 1.0, None))

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
    # Ensure Gemini only received the bounded text length
    mock_parser.parse_async.assert_called_once_with("A" * MAX_RESUME_TEXT_CHARS)
    
    # Check that update_resume_status was called with the truncated text
    call_kwargs = mock_resume_repo.update_resume_status.call_args.kwargs
    assert len(call_kwargs["raw_text"]) == MAX_RESUME_TEXT_CHARS
