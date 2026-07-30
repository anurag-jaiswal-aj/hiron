"""Unit tests for EmbeddingRepository candidate and job embedding DB operations."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from hiron.embeddings.models import JobEmbedding
from hiron.embeddings.repository import EmbeddingRepository


@pytest.mark.asyncio
async def test_upsert_candidate_embedding_create_new() -> None:
    """Verify upsert_candidate_embedding adds new candidate embedding record."""
    repo = EmbeddingRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    vector = [0.1] * 1536

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_result)

    result = await repo.upsert_candidate_embedding(
        session=session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        embedding=vector,
        model_version="text-embedding-3-small",
        source_text_hash="hash123",
    )

    assert result.tenant_id == tenant_id
    assert result.candidate_id == candidate_id
    assert result.source_text_hash == "hash123"
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_upsert_job_embedding_update_existing() -> None:
    """Verify upsert_job_embedding updates existing job embedding record."""
    repo = EmbeddingRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    vector = [0.2] * 1536

    existing = JobEmbedding(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        embedding=[0.1] * 1536,
        model_version="text-embedding-3-small",
        source_text_hash="old_hash",
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing
    session.execute = AsyncMock(return_value=mock_result)

    result = await repo.upsert_job_embedding(
        session=session,
        tenant_id=tenant_id,
        job_id=job_id,
        embedding=vector,
        model_version="text-embedding-3-small",
        source_text_hash="new_hash",
    )

    assert result.source_text_hash == "new_hash"
    assert result.embedding == vector
    session.flush.assert_called_once()
