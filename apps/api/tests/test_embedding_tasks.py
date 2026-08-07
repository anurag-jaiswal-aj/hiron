"""Focused tests proving Checkpoint 1A celery architecture execution boundary."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hiron.embeddings.tasks import (
    _async_generate_candidate_embedding_task,
    _async_generate_job_embedding_task,
    generate_candidate_embedding,
    generate_job_embedding,
)


def test_candidate_task_registered_as_celery() -> None:
    """Prove candidate embedding task is registered as a real Celery task (A)."""
    assert hasattr(generate_candidate_embedding, "delay")
    assert generate_candidate_embedding.name == "hiron.embeddings.generate_candidate_embedding"


def test_job_task_registered_as_celery() -> None:
    """Prove job embedding task is registered as a real Celery task (B)."""
    assert hasattr(generate_job_embedding, "delay")
    assert generate_job_embedding.name == "hiron.embeddings.generate_job_embedding"


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.EmbeddingService")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
@patch("hiron.embeddings.tasks._save_telemetry")
async def test_candidate_task_opens_session_and_calls_service(
    mock_save_telemetry: AsyncMock, mock_session_local: AsyncMock, mock_service_class: AsyncMock
) -> None:
    """Prove candidate task opens DB session, calls pipeline, and commits (C, D, F, K, L)."""
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service

    result = await _async_generate_candidate_embedding_task(tenant_id, candidate_id, "test-model")

    assert result["status"] == "success"
    assert result["candidate_id"] == candidate_id

    # Assert session was committed
    mock_session.commit.assert_awaited_once()
    assert mock_save_telemetry.called

    # Assert service was called with correctly reconstructed UUIDs
    mock_service.generate_candidate_embedding_pipeline.assert_awaited_once_with(
        session=mock_session,
        tenant_id=uuid.UUID(tenant_id),
        candidate_id=uuid.UUID(candidate_id),
        model_version="test-model"
    )


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.EmbeddingService")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
@patch("hiron.embeddings.tasks._save_telemetry")
async def test_job_task_rolls_back_on_failure(
    mock_save_telemetry: AsyncMock, mock_session_local: AsyncMock, mock_service_class: AsyncMock
) -> None:
    """Prove job task rolls back on failure (G, E)."""
    tenant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session

    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service
    mock_service.generate_job_embedding_pipeline.side_effect = Exception("Test failure")

    with pytest.raises(Exception, match="Test failure"):
        await _async_generate_job_embedding_task(tenant_id, job_id, "test-model")

    # Assert rollback occurred
    mock_session.rollback.assert_awaited_once()
    mock_session.commit.assert_not_called()
    assert mock_save_telemetry.called

@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.EmbeddingService")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
@patch("hiron.embeddings.tasks._save_telemetry")
async def test_candidate_task_success_telemetry(
    mock_save_telemetry: AsyncMock, mock_session_local: AsyncMock, mock_service_class: AsyncMock
) -> None:
    """Verify genuine generation logs success telemetry."""
    from hiron.embeddings.service import PipelineResult
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service

    mock_service.generate_candidate_embedding_pipeline.return_value = PipelineResult(
        cache_hit=False,
        model_version="test-model",
        input_tokens=10,
        total_tokens=10,
        latency_ms=100,
        status="success",
        error_type=None,
    )

    await _async_generate_candidate_embedding_task(tenant_id, candidate_id, "test-model")

    mock_save_telemetry.assert_awaited_once_with(
        tenant_id=uuid.UUID(tenant_id),
        operation="candidate_embedding",
        model_version="test-model",
        input_tokens=10,
        output_tokens=0,
        cost_usd=0.0,
        latency_ms=100,
        status="success",
        error_type=None,
        is_cache_hit=False,
    )


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.EmbeddingService")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
@patch("hiron.embeddings.tasks._save_telemetry")
async def test_job_task_cache_hit_telemetry(
    mock_save_telemetry: AsyncMock, mock_session_local: AsyncMock, mock_service_class: AsyncMock
) -> None:
    """Verify cache hit logs is_cache_hit=True."""
    from hiron.embeddings.service import PipelineResult
    tenant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service

    mock_service.generate_job_embedding_pipeline.return_value = PipelineResult(
        cache_hit=True,
        model_version="test-model",
        input_tokens=0,
        total_tokens=0,
        latency_ms=0,
        status="success",
        error_type=None,
    )

    await _async_generate_job_embedding_task(tenant_id, job_id, "test-model")

    mock_save_telemetry.assert_awaited_once_with(
        tenant_id=uuid.UUID(tenant_id),
        operation="job_embedding",
        model_version="test-model",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        latency_ms=0,
        status="success",
        error_type=None,
        is_cache_hit=True,
    )


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.EmbeddingService")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
@patch("hiron.embeddings.tasks._save_telemetry")
async def test_job_task_failure_telemetry(
    mock_save_telemetry: AsyncMock, mock_session_local: AsyncMock, mock_service_class: AsyncMock
) -> None:
    """Verify production OpenAI failure rolls back and attempts error telemetry."""
    tenant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service

    class FakeOpenAIError(Exception):
        pass

    mock_service.generate_job_embedding_pipeline.side_effect = FakeOpenAIError("Terminal Production Error")

    with pytest.raises(FakeOpenAIError):
        await _async_generate_job_embedding_task(tenant_id, job_id, "test-model")

    mock_session.rollback.assert_awaited_once()
    mock_save_telemetry.assert_awaited_once_with(
        tenant_id=uuid.UUID(tenant_id),
        operation="job_embedding",
        model_version="test-model",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        latency_ms=0,
        status="error",
        error_type="FakeOpenAIError",
        is_cache_hit=False,
    )


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.EmbeddingService")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
@patch("hiron.ai_usage.repository.AIUsageRepository")
async def test_telemetry_failure_does_not_fail_successful_embedding_task(
    mock_ai_repo_class: MagicMock, mock_session_local: AsyncMock, mock_service_class: AsyncMock
) -> None:
    """Verify telemetry failure does not mask original success."""
    from hiron.embeddings.service import PipelineResult
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service

    mock_service.generate_candidate_embedding_pipeline.return_value = PipelineResult(
        cache_hit=False,
        model_version="test-model",
        input_tokens=10,
        total_tokens=10,
        latency_ms=100,
        status="success",
        error_type=None,
    )

    mock_repo = AsyncMock()
    mock_ai_repo_class.return_value = mock_repo
    mock_repo.create_usage_log.side_effect = Exception("Telemetry DB Failed")

    await _async_generate_candidate_embedding_task(tenant_id, candidate_id, "test-model")
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.EmbeddingService")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
@patch("hiron.ai_usage.repository.AIUsageRepository")
async def test_telemetry_failure_during_openai_failure_does_not_mask_original_exception(
    mock_ai_repo_class: MagicMock, mock_session_local: AsyncMock, mock_service_class: AsyncMock
) -> None:
    """Verify telemetry failure doesn't mask the original pipeline exception."""
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service

    mock_service.generate_candidate_embedding_pipeline.side_effect = ValueError("Original Exception")

    mock_repo = AsyncMock()
    mock_ai_repo_class.return_value = mock_repo
    mock_repo.create_usage_log.side_effect = Exception("Telemetry DB Failed")

    with pytest.raises(ValueError, match="Original Exception"):
        await _async_generate_candidate_embedding_task(tenant_id, candidate_id, "test-model")


@pytest.mark.asyncio
@patch("hiron.ai_usage.repository.AIUsageRepository")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
async def test_save_telemetry_uses_independent_session_and_commits(
    mock_session_local: AsyncMock, mock_ai_repo_class: MagicMock
) -> None:
    """Verify _save_telemetry uses independent session and commits."""
    from hiron.embeddings.tasks import _save_telemetry
    mock_session = AsyncMock()
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_repo = AsyncMock()
    mock_ai_repo_class.return_value = mock_repo

    tenant_id = uuid.uuid4()

    await _save_telemetry(
        tenant_id=tenant_id,
        operation="test_op",
        model_version="test-model",
        input_tokens=1,
        output_tokens=0,
        cost_usd=0.0,
        latency_ms=10,
        status="success",
        error_type=None,
        is_cache_hit=False,
    )

    mock_repo.create_usage_log.assert_awaited_once_with(
        session=mock_session,
        tenant_id=tenant_id,
        operation="test_op",
        model_version="test-model",
        input_tokens=1,
        output_tokens=0,
        cost_usd=0.0,
        latency_ms=10,
        status="success",
        error_type=None,
        is_cache_hit=False,
    )
    mock_session.commit.assert_awaited_once()


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.EmbeddingService")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
@patch("hiron.embeddings.tasks._save_telemetry")
async def test_candidate_task_commit_failure_after_success_propagates(
    mock_save_telemetry: AsyncMock, mock_session_local: AsyncMock, mock_service_class: AsyncMock
) -> None:
    """Verify session commit failure after successful pipeline raises exception."""
    from hiron.embeddings.service import PipelineResult
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    mock_session = AsyncMock()

    class FakeCommitError(Exception):
        pass

    mock_session.commit.side_effect = FakeCommitError("commit failed")
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service

    mock_service.generate_candidate_embedding_pipeline.return_value = PipelineResult(
        cache_hit=False,
        model_version="test-model",
        input_tokens=10,
        total_tokens=10,
        latency_ms=100,
        status="success",
        error_type=None,
    )

    with pytest.raises(FakeCommitError, match="commit failed"):
        await _async_generate_candidate_embedding_task(tenant_id, candidate_id, "test-model")

    mock_session.rollback.assert_awaited_once()
    mock_save_telemetry.assert_awaited_once_with(
        tenant_id=uuid.UUID(tenant_id),
        operation="candidate_embedding",
        model_version="test-model",
        input_tokens=10,
        output_tokens=0,
        cost_usd=0.0,
        latency_ms=100,
        status="success",
        error_type=None,
        is_cache_hit=False,
    )


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.EmbeddingService")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
@patch("hiron.embeddings.tasks._save_telemetry")
async def test_job_task_commit_failure_after_success_propagates(
    mock_save_telemetry: AsyncMock, mock_session_local: AsyncMock, mock_service_class: AsyncMock
) -> None:
    """Verify session commit failure after successful job pipeline raises exception."""
    from hiron.embeddings.service import PipelineResult
    tenant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    mock_session = AsyncMock()

    class FakeCommitError(Exception):
        pass

    mock_session.commit.side_effect = FakeCommitError("commit failed")
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service

    mock_service.generate_job_embedding_pipeline.return_value = PipelineResult(
        cache_hit=False,
        model_version="test-model",
        input_tokens=20,
        total_tokens=20,
        latency_ms=150,
        status="success",
        error_type=None,
    )

    with pytest.raises(FakeCommitError, match="commit failed"):
        await _async_generate_job_embedding_task(tenant_id, job_id, "test-model")

    mock_session.rollback.assert_awaited_once()
    mock_save_telemetry.assert_awaited_once_with(
        tenant_id=uuid.UUID(tenant_id),
        operation="job_embedding",
        model_version="test-model",
        input_tokens=20,
        output_tokens=0,
        cost_usd=0.0,
        latency_ms=150,
        status="success",
        error_type=None,
        is_cache_hit=False,
    )


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.EmbeddingService")
@patch("hiron.embeddings.tasks.AsyncSessionLocal")
@patch("hiron.ai_usage.repository.AIUsageRepository")
async def test_telemetry_failure_during_commit_failure_propagates_commit_error(
    mock_ai_repo_class: MagicMock, mock_session_local: AsyncMock, mock_service_class: AsyncMock
) -> None:
    """Verify telemetry failure during a DB commit failure still propagates the DB error."""
    from hiron.embeddings.service import PipelineResult
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())

    mock_session = AsyncMock()

    class FakeCommitError(Exception):
        pass

    mock_session.commit.side_effect = FakeCommitError("commit failed")
    mock_session_local.return_value.__aenter__.return_value = mock_session
    mock_service = AsyncMock()
    mock_service_class.return_value = mock_service

    mock_service.generate_candidate_embedding_pipeline.return_value = PipelineResult(
        cache_hit=False,
        model_version="test-model",
        input_tokens=10,
        total_tokens=10,
        latency_ms=100,
        status="success",
        error_type=None,
    )

    mock_repo = AsyncMock()
    mock_ai_repo_class.return_value = mock_repo
    class TelemetryError(Exception):
        pass
    mock_repo.create_usage_log.side_effect = TelemetryError("Telemetry failed")

    with pytest.raises(FakeCommitError, match="commit failed"):
        await _async_generate_candidate_embedding_task(tenant_id, candidate_id, "test-model")

    mock_session.rollback.assert_awaited_once()
