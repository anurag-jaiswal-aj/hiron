import uuid
from unittest.mock import AsyncMock, patch

import pytest

from hiron.candidates.models import Candidate
from hiron.resumes.models import Resume, ResumeFile
from apps.worker.src.pipeline import parse_resume_pipeline


@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.ResumeRepository")
@patch("apps.worker.src.pipeline.CandidateRepository")
@patch("apps.worker.src.pipeline.extract_text_from_file")
@patch("apps.worker.src.pipeline.ResumeParser")
@patch("hiron.storage.provider.LocalStorageProvider")
@patch("hiron.core.qstash_client.qstash_publisher")
@patch("hiron.core.config.get_settings")
async def test_parse_resume_triggers_candidate_embedding(
    mock_get_settings,
    mock_qstash_publisher,
    mock_local_storage_cls,
    mock_parser_cls,
    mock_extract_text_from_file,
    mock_cand_repo_cls,
    mock_resume_repo_cls,
):
    """Verify that a successful parse triggers a candidate embedding QStash publish."""
    session = AsyncMock()
    
    mock_storage = mock_local_storage_cls.return_value
    mock_storage.download_file = AsyncMock(return_value=b"resume content")
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_resume_repo = mock_resume_repo_cls.return_value
    mock_cand_repo = mock_cand_repo_cls.return_value

    mock_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="pending"
    )
    mock_resume_repo.get_resume_by_id = AsyncMock(return_value=mock_resume)
    
    mock_resume_file = ResumeFile(
        s3_key="foo", original_filename="bar", content_type="text/plain"
    )
    mock_resume_repo.get_resume_file_by_resume_id = AsyncMock(return_value=mock_resume_file)

    mock_extract_text_from_file.return_value = "parsed text"

    mock_parser = mock_parser_cls.return_value
    mock_parser.model_version = "v1"
    mock_parser.parse.return_value = ({"skills": ["Python"]}, 1.0, None)

    parsed_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="parsed"
    )
    mock_resume_repo.update_resume_status = AsyncMock(return_value=parsed_resume)
    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="John Doe"
    ))

    mock_settings = mock_get_settings.return_value
    mock_settings.worker_url = "http://worker:8000"
    mock_settings.supabase_url = None
    mock_settings.supabase_service_role_key = None

    result = await parse_resume_pipeline(session, tenant_id, resume_id)

    assert result.status == "parsed"

    # Verify QStash publish
    mock_qstash_publisher.publish.assert_called_once()
    call_args = mock_qstash_publisher.publish.call_args.kwargs
    assert call_args["url"] == "http://worker:8000/api/v1/webhooks/qstash/embeddings/candidate"
    assert call_args["payload"]["tenant_id"] == str(tenant_id)
    assert call_args["payload"]["candidate_id"] == str(candidate_id)
    assert call_args["payload"]["model_version"] == "gemini-embedding-2"
    assert call_args["deduplication_id"] == f"embed-cand-{candidate_id}-gemini-embedding-2"


@pytest.mark.asyncio
@patch("apps.worker.src.pipeline.ResumeRepository")
@patch("apps.worker.src.pipeline.CandidateRepository")
@patch("apps.worker.src.pipeline.extract_text_from_file")
@patch("apps.worker.src.pipeline.ResumeParser")
@patch("hiron.storage.provider.LocalStorageProvider")
@patch("hiron.core.qstash_client.qstash_publisher")
@patch("hiron.core.config.get_settings")
async def test_parse_resume_trigger_failure_swallowed(
    mock_get_settings,
    mock_qstash_publisher,
    mock_local_storage_cls,
    mock_parser_cls,
    mock_extract_text_from_file,
    mock_cand_repo_cls,
    mock_resume_repo_cls,
):
    """Verify that a QStash publish failure does not crash the parse pipeline."""
    session = AsyncMock()
    
    mock_storage = mock_local_storage_cls.return_value
    mock_storage.download_file = AsyncMock(return_value=b"resume content")
    tenant_id = uuid.uuid4()
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_resume_repo = mock_resume_repo_cls.return_value
    mock_cand_repo = mock_cand_repo_cls.return_value

    mock_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="pending"
    )
    mock_resume_repo.get_resume_by_id = AsyncMock(return_value=mock_resume)
    mock_resume_file = ResumeFile(
        s3_key="foo", original_filename="bar", content_type="text/plain"
    )
    mock_resume_repo.get_resume_file_by_resume_id = AsyncMock(return_value=mock_resume_file)

    mock_extract_text_from_file.return_value = "parsed text"

    mock_parser = mock_parser_cls.return_value
    mock_parser.model_version = "v1"
    mock_parser.parse.return_value = ({"skills": ["Python"]}, 1.0, None)

    parsed_resume = Resume(
        id=resume_id, tenant_id=tenant_id, candidate_id=candidate_id, status="parsed"
    )
    mock_resume_repo.update_resume_status = AsyncMock(return_value=parsed_resume)
    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="John Doe"
    ))

    mock_settings = mock_get_settings.return_value
    mock_settings.worker_url = "http://worker:8000"
    mock_settings.supabase_url = None
    mock_settings.supabase_service_role_key = None

    # Simulate QStash network failure
    mock_qstash_publisher.publish.side_effect = Exception("Network error")

    # The pipeline should handle the exception and return the successfully parsed resume
    result = await parse_resume_pipeline(session, tenant_id, resume_id)
    
    assert result.status == "parsed"
    mock_qstash_publisher.publish.assert_called_once()
