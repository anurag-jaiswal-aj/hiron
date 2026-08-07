"""Focused tests proving Checkpoint 1A celery architecture execution boundary."""

import uuid
from unittest.mock import AsyncMock, patch

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
async def test_candidate_task_opens_session_and_calls_service(
    mock_session_local: AsyncMock, mock_service_class: AsyncMock
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
async def test_job_task_rolls_back_on_failure(
    mock_session_local: AsyncMock, mock_service_class: AsyncMock
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
