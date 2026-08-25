"""Tests for PII-safe logging helper per Phase H.2.5."""

import pytest
from pydantic import BaseModel, ValidationError

from apps.worker.src.pipeline import _get_safe_error_message
from hiron.resumes.exceptions import ResumeParseFailedError


def test_validation_error_safe_message() -> None:
    """Verify ValidationError does not leak input PII."""
    class MockModel(BaseModel):
        email: str

    try:
        MockModel(email="not-an-email-SECRET_RESUME_PII_12345")
    except ValidationError as exc:
        safe_msg = _get_safe_error_message(exc)
        assert "SECRET_RESUME_PII_12345" not in safe_msg
        assert safe_msg == "Resume schema validation failed"


def test_gemini_api_error_safe_message() -> None:
    """Verify Gemini APIError does not log raw message containing PII."""
    try:
        from google.genai.errors import APIError
    except ImportError:
        pytest.skip("google-genai not installed")

    exc = APIError(
        code=400,
        response_json={"error": {"status": "INVALID_ARGUMENT", "message": "Invalid request containing SECRET_RESUME_PII_12345"}},
    )
    safe_msg = _get_safe_error_message(exc)

    assert "SECRET_RESUME_PII_12345" not in safe_msg
    assert "400" in safe_msg
    assert "INVALID_ARGUMENT" in safe_msg
    assert "Gemini API error" in safe_msg


def test_timeout_error_safe_message() -> None:
    """Verify TimeoutError yields a safe category."""
    exc = TimeoutError("Connection to API containing SECRET_RESUME_PII_12345 timed out")
    safe_msg = _get_safe_error_message(exc)

    assert "SECRET_RESUME_PII_12345" not in safe_msg
    assert safe_msg == "Resume parsing timed out"


def test_unknown_exception_safe_message() -> None:
    """Verify unknown exceptions expose only their type."""
    exc = ValueError("Could not parse SECRET_RESUME_PII_12345")
    safe_msg = _get_safe_error_message(exc)

    assert "SECRET_RESUME_PII_12345" not in safe_msg
    assert safe_msg == "Resume parsing failed: ValueError"


def test_resume_parse_failed_error_safe_message() -> None:
    """Verify ResumeParseFailedError preserves its safe custom message."""
    exc = ResumeParseFailedError("PDF extraction failed: BadZipFile")
    safe_msg = _get_safe_error_message(exc)

    assert safe_msg == "PDF extraction failed: BadZipFile"


import uuid
from unittest.mock import AsyncMock, patch
from hiron.resumes.models import Resume

@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.logger")
@patch("apps.worker.src.pipeline.ResumeRepository")
@patch("apps.worker.src.pipeline.extract_text_from_file")
@patch("hiron.storage.provider.LocalStorageProvider")
async def test_pipeline_logging_boundary(
    mock_local_storage: AsyncMock,
    mock_extract: AsyncMock,
    mock_repo_class: AsyncMock,
    mock_logger: AsyncMock,
) -> None:
    """Verify parse_resume_pipeline boundary does not leak PII to logs or DB."""
    from apps.worker.src.pipeline import parse_resume_pipeline

    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()

    mock_repo = mock_repo_class.return_value
    mock_resume = Resume(
        id=resume_id,
        tenant_id=tenant_id,
        candidate_id=uuid.uuid4(),
        status="pending",
    )
    mock_repo.get_resume_by_id = AsyncMock(return_value=mock_resume)
    from unittest.mock import MagicMock
    mock_file = MagicMock()
    mock_file.s3_key = "test.pdf"
    mock_repo.get_resume_file_by_resume_id = AsyncMock(return_value=mock_file)
    mock_repo.update_resume_status = AsyncMock()

    mock_local_storage.return_value.download_file = AsyncMock(return_value=b"test")

    # Simulate an exception deep inside the pipeline containing PII
    mock_extract.side_effect = ValueError("Fatal extraction error containing SECRET_RESUME_PII_12345")

    mock_session = AsyncMock()

    with pytest.raises(ValueError, match=r".*SECRET_RESUME_PII_12345.*"):
        await parse_resume_pipeline(
            session=mock_session,
            tenant_id=tenant_id,
            resume_id=resume_id,
        )

    # 1. Assert logger boundary
    mock_logger.warning.assert_called()
    _log_args, log_kwargs = mock_logger.warning.call_args
    assert "SECRET_RESUME_PII_12345" not in log_kwargs.get("error", "")
    assert "ValueError" in log_kwargs.get("error", "")

    # 2. Assert database boundary
    mock_repo.update_resume_status.assert_called()
    _db_args, db_kwargs = mock_repo.update_resume_status.call_args
    assert "SECRET_RESUME_PII_12345" not in db_kwargs.get("parse_error", "")
    assert "ValueError" in db_kwargs.get("parse_error", "")


@pytest.mark.asyncio
@patch("apps.worker.src.main.logger")
@patch("apps.worker.src.main.parse_resume_pipeline")
@patch("apps.worker.src.main.AsyncSessionLocal")
async def test_main_webhook_logging_boundary(
    mock_session_local: AsyncMock,
    mock_pipeline: AsyncMock,
    mock_logger: AsyncMock,
) -> None:
    """Verify parse_resume_webhook boundary does not leak PII to top-level logs."""
    from apps.worker.src.main import parse_resume_webhook

    class FakePayload:
        tenant_id = uuid.uuid4()
        resume_id = uuid.uuid4()

    # Simulate an exception bubbling up to the webhook containing PII
    mock_pipeline.side_effect = ValueError("Pipeline failed with SECRET_RESUME_PII_12345")

    mock_session_local.return_value.__aenter__.return_value = AsyncMock()

    with pytest.raises(ValueError, match=r".*SECRET_RESUME_PII_12345.*"):
        await parse_resume_webhook(FakePayload())

    # Assert logger boundary
    mock_logger.error.assert_called()
    _log_args, log_kwargs = mock_logger.error.call_args

    # Main logger should NOT use 'error' with raw string
    assert "error" not in log_kwargs
    # Should use 'error_type' instead
    assert log_kwargs.get("error_type") == "ValueError"
    assert "SECRET_RESUME_PII_12345" not in str(log_kwargs)
    assert "SECRET_RESUME_PII_12345" not in str(_log_args)
