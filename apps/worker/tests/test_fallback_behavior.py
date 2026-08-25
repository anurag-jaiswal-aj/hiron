import uuid
import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from google.genai.errors import APIError
from pydantic import ValidationError
from apps.worker.src.pipeline import _parse_resume_with_gemini_fallback

@pytest.fixture
def mock_session():
    session = AsyncMock()
    session.begin_nested = AsyncMock()
    return session

@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.GeminiResumeParser")
@patch("apps.worker.src.pipeline.ResumeParser")
async def test_gemini_429_propagates_without_fallback(mock_legacy_parser_cls, mock_gemini_parser_cls, mock_session):
    mock_gemini = AsyncMock()
    mock_gemini.model_version = "test-model"
    error = APIError(code=429, response_json={}, response=None)
    mock_gemini.parse_async.side_effect = error
    mock_gemini_parser_cls.return_value = mock_gemini

    tenant_id = uuid.uuid4()

    with pytest.raises(APIError) as exc_info:
        await _parse_resume_with_gemini_fallback(mock_session, tenant_id, "Test resume text")

    assert exc_info.value.code == 429
    mock_legacy_parser_cls.assert_not_called()
    mock_session.begin_nested.assert_called_once()

@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.GeminiResumeParser")
@patch("apps.worker.src.pipeline.ResumeParser")
async def test_gemini_500_propagates_without_fallback(mock_legacy_parser_cls, mock_gemini_parser_cls, mock_session):
    mock_gemini = AsyncMock()
    mock_gemini.model_version = "test-model"
    error = APIError(code=500, response_json={}, response=None)
    mock_gemini.parse_async.side_effect = error
    mock_gemini_parser_cls.return_value = mock_gemini

    tenant_id = uuid.uuid4()

    with pytest.raises(APIError) as exc_info:
        await _parse_resume_with_gemini_fallback(mock_session, tenant_id, "Test resume text")

    assert exc_info.value.code == 500
    mock_legacy_parser_cls.assert_not_called()
    mock_session.begin_nested.assert_called_once()

@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.GeminiResumeParser")
@patch("apps.worker.src.pipeline.ResumeParser")
async def test_gemini_503_propagates_without_fallback(mock_legacy_parser_cls, mock_gemini_parser_cls, mock_session):
    mock_gemini = AsyncMock()
    mock_gemini.model_version = "test-model"
    error = APIError(code=503, response_json={}, response=None)
    mock_gemini.parse_async.side_effect = error
    mock_gemini_parser_cls.return_value = mock_gemini

    tenant_id = uuid.uuid4()

    with pytest.raises(APIError) as exc_info:
        await _parse_resume_with_gemini_fallback(mock_session, tenant_id, "Test resume text")

    assert exc_info.value.code == 503
    mock_legacy_parser_cls.assert_not_called()
    mock_session.begin_nested.assert_called_once()

@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.GeminiResumeParser")
@patch("apps.worker.src.pipeline.ResumeParser")
async def test_gemini_timeout_propagates_without_fallback(mock_legacy_parser_cls, mock_gemini_parser_cls, mock_session):
    mock_gemini = AsyncMock()
    mock_gemini.model_version = "test-model"
    error = TimeoutError("Timeout")
    mock_gemini.parse_async.side_effect = error
    mock_gemini_parser_cls.return_value = mock_gemini

    tenant_id = uuid.uuid4()

    with pytest.raises(asyncio.TimeoutError):
        await _parse_resume_with_gemini_fallback(mock_session, tenant_id, "Test resume text")

    mock_legacy_parser_cls.assert_not_called()
    mock_session.begin_nested.assert_called_once()

@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.GeminiResumeParser")
@patch("apps.worker.src.pipeline.ResumeParser")
async def test_gemini_validation_error_falls_back(mock_legacy_parser_cls, mock_gemini_parser_cls, mock_session):
    mock_gemini = AsyncMock()
    mock_gemini.model_version = "test-model"

    from pydantic import BaseModel
    class DummyModel(BaseModel):
        x: int
    def make_validation_error():
        try:
            DummyModel(x="not an int")
        except ValidationError as e:
            return e

    mock_gemini.parse_async.side_effect = make_validation_error()
    mock_gemini_parser_cls.return_value = mock_gemini

    mock_legacy = MagicMock()
    mock_legacy.model_version = "legacy-model"
    mock_legacy.parse.return_value = ({"full_name": "Fallback Name"}, 1.0, {})
    mock_legacy_parser_cls.return_value = mock_legacy

    tenant_id = uuid.uuid4()

    result, confidence, _, _ = await _parse_resume_with_gemini_fallback(mock_session, tenant_id, "Test resume text")

    assert result["full_name"] == "Fallback Name"
    assert confidence == 1.0
    mock_legacy.parse.assert_called_once_with("Test resume text")
    mock_session.begin_nested.assert_called_once()

@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.GeminiResumeParser")
@patch("apps.worker.src.pipeline.ResumeParser")
async def test_gemini_400_falls_back(mock_legacy_parser_cls, mock_gemini_parser_cls, mock_session):
    mock_gemini = AsyncMock()
    mock_gemini.model_version = "test-model"
    error = APIError(code=400, response_json={}, response=None)
    mock_gemini.parse_async.side_effect = error
    mock_gemini_parser_cls.return_value = mock_gemini

    mock_legacy = MagicMock()
    mock_legacy.model_version = "legacy-model"
    mock_legacy.parse.return_value = ({"full_name": "Fallback Name 400"}, 0.8, {})
    mock_legacy_parser_cls.return_value = mock_legacy

    tenant_id = uuid.uuid4()

    result, confidence, _, _ = await _parse_resume_with_gemini_fallback(mock_session, tenant_id, "Test resume text")

    assert result["full_name"] == "Fallback Name 400"
    assert confidence == 0.8
    mock_legacy.parse.assert_called_once_with("Test resume text")
    mock_session.begin_nested.assert_called_once()

@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.GeminiResumeParser")
@patch("apps.worker.src.pipeline.ResumeParser")
async def test_unknown_gemini_error_behavior(mock_legacy_parser_cls, mock_gemini_parser_cls, mock_session):
    mock_gemini = AsyncMock()
    mock_gemini.model_version = "test-model"
    error = RuntimeError("Some unknown internal error")
    mock_gemini.parse_async.side_effect = error
    mock_gemini_parser_cls.return_value = mock_gemini

    tenant_id = uuid.uuid4()

    with pytest.raises(RuntimeError):
        await _parse_resume_with_gemini_fallback(mock_session, tenant_id, "Test resume text")

    mock_legacy_parser_cls.assert_not_called()
    mock_session.begin_nested.assert_called_once()
