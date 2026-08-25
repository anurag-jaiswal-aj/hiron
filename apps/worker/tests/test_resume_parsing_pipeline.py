import uuid
from unittest.mock import AsyncMock, patch

import pytest
from apps.worker.src.pipeline import parse_resume_pipeline

from hiron.candidates.models import Candidate
from hiron.resumes.models import Resume, ResumeFile


@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.ResumeRepository")
@patch("apps.worker.src.pipeline.CandidateRepository")
@patch("apps.worker.src.pipeline.extract_text_from_file")
@patch("apps.worker.src.pipeline.ResumeParser")
@patch("hiron.storage.provider.LocalStorageProvider")
@patch("hiron.core.qstash_client.qstash_publisher")
@patch("hiron.core.config.get_settings")
@patch("hiron.ai_usage.repository.AIUsageRepository")
@patch("apps.worker.src.pipeline.GeminiResumeParser")
async def test_pipeline_gemini_api_failure_fallback(
    mock_gemini_parser_cls,
    mock_ai_repo_cls,
    mock_get_settings,
    mock_qstash_publisher,
    mock_local_storage_cls,
    mock_parser_cls,
    mock_extract_text_from_file,
    mock_cand_repo_cls,
    mock_resume_repo_cls,
):
    """Verify that Gemini API failure falls back to deterministic parser and logs error telemetry."""
    session = AsyncMock()
    from unittest.mock import MagicMock
    session.begin_nested = MagicMock()
    session.begin_nested.return_value.__aenter__ = AsyncMock()
    session.begin_nested.return_value.__aexit__ = AsyncMock()

    mock_ai_repo = mock_ai_repo_cls.return_value
    mock_ai_repo.create_usage_log = AsyncMock()

    mock_storage = mock_local_storage_cls.return_value
    mock_storage.download_file = AsyncMock(return_value=b"resume content")
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_resume_repo = mock_resume_repo_cls.return_value
    mock_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="pending"
    )
    mock_resume_repo.get_resume_by_id = AsyncMock(return_value=mock_resume)

    mock_resume_file = ResumeFile(
        s3_key="foo", original_filename="bar", content_type="text/plain"
    )
    mock_resume_repo.get_resume_file_by_resume_id = AsyncMock(return_value=mock_resume_file)

    mock_extract_text_from_file.return_value = ("parsed text", False)

    from google.genai.errors import APIError
    
    # 1. Gemini fails with a permanent error that should trigger fallback
    mock_gemini_parser = mock_gemini_parser_cls.return_value
    mock_gemini_parser.model_version = "gemini-1.5-flash"
    mock_gemini_parser.parse_async = AsyncMock(side_effect=APIError(code=400, response=None, response_json={}))

    # 2. Deterministic parser succeeds
    mock_parser = mock_parser_cls.return_value
    mock_parser.model_version = "spacy-mock"
    mock_parser.parse.return_value = (
        {"skills": ["FallbackSkill"]},
        0.5,
        {
            "model_version": "spacy-mock",
            "latency_ms": 100,
            "status": "success",
            "error_type": None,
            "input_tokens": 0,
            "output_tokens": 0,
            "cost_usd": 0.0,
        }
    )

    parsed_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="parsed"
    )
    mock_resume_repo.update_resume_status = AsyncMock(return_value=parsed_resume)
    
    mock_settings = mock_get_settings.return_value
    mock_settings.worker_url = "http://worker:8000"
    mock_settings.supabase_url = None
    mock_settings.supabase_service_role_key = None
    
    mock_cand_repo = mock_cand_repo_cls.return_value
    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="John Doe"
    ))

    result = await parse_resume_pipeline(session, tenant_id, resume_id)

    assert result.status == "parsed"

    # AI telemetry should be called TWICE: once for Gemini failure, once for SpaCy success
    assert mock_ai_repo.create_usage_log.call_count == 2
    
    # First call: Gemini failure
    gemini_call = mock_ai_repo.create_usage_log.call_args_list[0].kwargs
    assert gemini_call["model_version"] == "gemini-1.5-flash"
    assert gemini_call["status"] == "error"
    assert gemini_call["error_type"] == "APIError"
    assert gemini_call["input_tokens"] == 0
    
    # Second call: Deterministic success
    spacy_call = mock_ai_repo.create_usage_log.call_args_list[1].kwargs
    assert spacy_call["model_version"] == "spacy-mock"
    assert spacy_call["status"] == "success"

@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.ResumeRepository")
@patch("apps.worker.src.pipeline.CandidateRepository")
@patch("apps.worker.src.pipeline.extract_text_from_file")
@patch("apps.worker.src.pipeline.ResumeParser")
@patch("hiron.storage.provider.LocalStorageProvider")
@patch("hiron.core.qstash_client.qstash_publisher")
@patch("hiron.core.config.get_settings")
@patch("hiron.ai_usage.repository.AIUsageRepository")
@patch("apps.worker.src.pipeline.GeminiResumeParser")
async def test_pipeline_empty_text_skips_gemini(
    mock_gemini_parser_cls,
    mock_ai_repo_cls,
    mock_get_settings,
    mock_qstash_publisher,
    mock_local_storage_cls,
    mock_parser_cls,
    mock_extract_text_from_file,
    mock_cand_repo_cls,
    mock_resume_repo_cls,
):
    """Verify that an empty resume skips Gemini and uses the deterministic parser."""
    session = AsyncMock()

    mock_storage = mock_local_storage_cls.return_value
    mock_storage.download_file = AsyncMock(return_value=b"resume content")
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_resume_repo = mock_resume_repo_cls.return_value
    mock_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="pending"
    )
    mock_resume_repo.get_resume_by_id = AsyncMock(return_value=mock_resume)

    mock_resume_file = ResumeFile(
        s3_key="foo", original_filename="bar", content_type="text/plain"
    )
    mock_resume_repo.get_resume_file_by_resume_id = AsyncMock(return_value=mock_resume_file)

    # Empty text!
    mock_extract_text_from_file.return_value = ("   \n  ", False)

    mock_parser = mock_parser_cls.return_value
    mock_parser.model_version = "spacy-mock"
    mock_parser.parse.return_value = ({"skills": []}, 0.0, None)

    parsed_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="parsed"
    )
    mock_resume_repo.update_resume_status = AsyncMock(return_value=parsed_resume)
    
    mock_settings = mock_get_settings.return_value
    mock_settings.worker_url = "http://worker:8000"
    mock_settings.supabase_url = None
    mock_settings.supabase_service_role_key = None
    
    mock_cand_repo = mock_cand_repo_cls.return_value
    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="John Doe"
    ))

    result = await parse_resume_pipeline(session, tenant_id, resume_id)

    assert result.status == "parsed"

    # Gemini parser should NEVER be instantiated or called
    mock_gemini_parser_cls.assert_not_called()
    mock_parser.parse.assert_called_once_with("   \n  ")
