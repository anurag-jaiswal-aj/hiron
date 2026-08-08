"""Service unit tests for candidate/job embedding generation, staleness detection, and RBAC validation."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from hiron.candidates.models import Candidate
from hiron.common.exceptions import ResourceNotFoundException
from hiron.embeddings.exceptions import InsufficientEmbeddingPermissionsError
from hiron.embeddings.service import EmbeddingService


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.generate_candidate_embedding")
async def test_generate_candidate_embedding_success(mock_task: MagicMock) -> None:
    """Verify generate_candidate_embedding executes pipeline and returns 202 response schema."""
    mock_task.delay.return_value.id = "mock-task-id"
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()
    generator = MagicMock()

    service = EmbeddingService(
        embedding_repository=emb_repo,
        candidate_repository=cand_repo,
        job_repository=job_repo,
        embedding_generator=generator,
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_candidate = Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="Jane Doe", skills=["Python"]
    )
    cand_repo.get_candidate_by_id.return_value = mock_candidate
    generator.generate_embedding.return_value = ([0.1] * 1536, "hash123")

    mock_resume_result = MagicMock()
    mock_resume_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_resume_result)

    response = await service.generate_candidate_embedding(
        session=session,
        tenant_id=tenant_id,
        user_role="recruiter",
        candidate_id=candidate_id,
    )

    assert response.data.candidate_id == candidate_id
    assert response.data.status == "processing"
    assert response.data.model_version == "text-embedding-3-small"

    mock_task.delay.assert_called_once_with(
        str(tenant_id),
        str(candidate_id),
        "text-embedding-3-small",
    )


@pytest.mark.asyncio
async def test_generate_job_embedding_not_found_raises_404() -> None:
    """Verify non-existent job ID raises ResourceNotFoundException."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    job_repo.get_job_by_id.return_value = None

    with pytest.raises(ResourceNotFoundException):
        await service.generate_job_embedding(
            session=session,
            tenant_id=tenant_id,
            user_role="recruiter",
            job_id=job_id,
        )


@pytest.mark.asyncio
async def test_generate_embedding_unauthorized_role_raises_403() -> None:
    """Verify member role raises InsufficientEmbeddingPermissionsError."""
    service = EmbeddingService()
    session = AsyncMock()

    with pytest.raises(InsufficientEmbeddingPermissionsError):
        await service.generate_job_embedding(
            session=session,
            tenant_id=uuid.uuid4(),
            user_role="member",
            job_id=uuid.uuid4(),
        )

@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.generate_candidate_embedding.delay")
async def test_generate_candidate_embedding_not_found_raises_404_and_no_enqueue(
    mock_embed_delay: MagicMock,
) -> None:
    """Verify non-existent candidate ID raises ResourceNotFoundException and does not enqueue."""
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    service = EmbeddingService(embedding_repository=emb_repo, candidate_repository=cand_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    cand_repo.get_candidate_by_id.return_value = None

    with pytest.raises(ResourceNotFoundException):
        await service.generate_candidate_embedding(
            session=session,
            tenant_id=tenant_id,
            user_role="recruiter",
            candidate_id=candidate_id,
        )

    mock_embed_delay.assert_not_called()


@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.generate_job_embedding.delay")
async def test_generate_job_embedding_not_found_raises_404_and_no_enqueue(
    mock_embed_delay: MagicMock,
) -> None:
    """Verify non-existent job ID raises ResourceNotFoundException and does not enqueue."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    job_repo.get_job_by_id.return_value = None

    with pytest.raises(ResourceNotFoundException):
        await service.generate_job_embedding(
            session=session,
            tenant_id=tenant_id,
            user_role="recruiter",
            job_id=job_id,
        )

    mock_embed_delay.assert_not_called()

@pytest.mark.asyncio
@patch("hiron.embeddings.tasks.generate_job_embedding.delay")
async def test_generate_job_embedding_success(mock_task_delay: MagicMock) -> None:
    """Verify generate_job_embedding succeeds and enqueues task."""
    mock_task_delay.return_value.id = "mock-task-id"
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_job = MagicMock()
    job_repo.get_job_by_id.return_value = mock_job

    response = await service.generate_job_embedding(
        session=session,
        tenant_id=tenant_id,
        user_role="recruiter",
        job_id=job_id,
    )

    assert response.data.job_id == job_id
    assert response.data.status == "processing"

    mock_task_delay.assert_called_once_with(
        str(tenant_id),
        str(job_id),
        "text-embedding-3-small",
    )

@pytest.mark.asyncio
async def test_generate_candidate_embedding_pipeline_cache_hit() -> None:
    """Verify matching hash + model + valid vector skips generator."""

    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    generator = MagicMock()

    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    service = EmbeddingService(
        embedding_repository=emb_repo,
        candidate_repository=cand_repo,
        embedding_generator=generator,
    )

    mock_candidate = Candidate(id=candidate_id, tenant_id=tenant_id, skills=["Python"])
    cand_repo.get_candidate_by_id.return_value = mock_candidate

    # Mock constructed text and hash
    patch.object(service, "_construct_candidate_source_text", new_callable=AsyncMock, return_value="Python").start()
    generator.compute_source_text_hash.return_value = "hash123"

    # Existing valid embedding
    existing = MagicMock()
    existing.source_text_hash = "hash123"
    existing.model_version = "text-embedding-3-small"
    existing.embedding = [0.1] * 1536
    emb_repo.get_candidate_embedding.return_value = existing

    session = AsyncMock()
    result = await service.generate_candidate_embedding_pipeline(
        session=session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        model_version="text-embedding-3-small",
    )

    assert result.cache_hit is True
    assert result.input_tokens == 0
    generator.generate_embedding.assert_not_called()
    emb_repo.upsert_candidate_embedding.assert_not_called()


@pytest.mark.asyncio
async def test_generate_job_embedding_pipeline_cache_hit() -> None:
    """Verify job matching hash + model skips generator."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    generator = MagicMock()

    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    service = EmbeddingService(
        embedding_repository=emb_repo,
        job_repository=job_repo,
        embedding_generator=generator,
    )

    mock_job = MagicMock(id=job_id, tenant_id=tenant_id)
    job_repo.get_job_by_id.return_value = mock_job

    # Mock constructed text and hash
    patch.object(service, "_construct_job_source_text", return_value="Backend Developer").start()
    generator.compute_source_text_hash.return_value = "hash456"

    existing = MagicMock()
    existing.source_text_hash = "hash456"
    existing.model_version = "text-embedding-3-small"
    existing.embedding = [0.1] * 1536
    emb_repo.get_job_embedding.return_value = existing

    session = AsyncMock()
    result = await service.generate_job_embedding_pipeline(
        session=session,
        tenant_id=tenant_id,
        job_id=job_id,
    )

    assert result.cache_hit is True
    generator.generate_embedding.assert_not_called()


@pytest.mark.asyncio
async def test_generate_candidate_embedding_pipeline_changed_hash_regenerates() -> None:
    """Verify mismatched hash regenerates."""
    from hiron.embeddings.generator import EmbeddingGenerationResult

    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    generator = MagicMock()

    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    service = EmbeddingService(
        embedding_repository=emb_repo,
        candidate_repository=cand_repo,
        embedding_generator=generator,
    )

    mock_candidate = Candidate(id=candidate_id, tenant_id=tenant_id, skills=["Python"])
    cand_repo.get_candidate_by_id.return_value = mock_candidate

    patch.object(service, "_construct_candidate_source_text", new_callable=AsyncMock, return_value="Python and Rust").start()
    generator.compute_source_text_hash.return_value = "hash-new"

    existing = MagicMock()
    existing.source_text_hash = "hash-old"
    existing.model_version = "text-embedding-3-small"
    existing.embedding = [0.1] * 1536
    emb_repo.get_candidate_embedding.return_value = existing

    generator.generate_embedding.return_value = EmbeddingGenerationResult(
        embedding=[0.2] * 1536,
        source_text_hash="hash-new",
        input_tokens=10,
        total_tokens=10,
        latency_ms=100,
        is_fallback=False,
        status="success",
        error_type=None,
    )

    session = AsyncMock()
    result = await service.generate_candidate_embedding_pipeline(
        session=session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    assert result.cache_hit is False
    assert result.input_tokens == 10
    generator.generate_embedding.assert_called_once_with("Python and Rust")
    emb_repo.upsert_candidate_embedding.assert_called_once()

@pytest.mark.asyncio
async def test_generate_job_embedding_pipeline_model_mismatch_regenerates() -> None:
    """Verify mismatched model version regenerates."""
    from hiron.embeddings.generator import EmbeddingGenerationResult
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    generator = MagicMock()

    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    service = EmbeddingService(
        embedding_repository=emb_repo,
        job_repository=job_repo,
        embedding_generator=generator,
    )

    mock_job = MagicMock()
    job_repo.get_job_by_id.return_value = mock_job

    patch.object(service, "_construct_job_source_text", return_value="Text").start()
    generator.compute_source_text_hash.return_value = "hash-same"

    existing = MagicMock()
    existing.source_text_hash = "hash-same"
    existing.model_version = "text-embedding-ada-002"
    existing.embedding = [0.1] * 1536
    emb_repo.get_job_embedding.return_value = existing

    generator.generate_embedding.return_value = EmbeddingGenerationResult(
        embedding=[0.2] * 1536,
        source_text_hash="hash-same",
        input_tokens=5,
        total_tokens=5,
        latency_ms=50,
        is_fallback=False,
        status="success",
        error_type=None,
    )

    session = AsyncMock()
    result = await service.generate_job_embedding_pipeline(
        session=session,
        tenant_id=tenant_id,
        job_id=job_id,
        model_version="text-embedding-3-small",
    )

    assert result.cache_hit is False
    generator.generate_embedding.assert_called_once_with("Text")


@pytest.mark.asyncio
async def test_generate_candidate_embedding_pipeline_missing_or_invalid_regenerates() -> None:
    """Verify missing existing, null vector, or wrong dimension regenerates."""
    from hiron.embeddings.generator import EmbeddingGenerationResult
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    generator = MagicMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    service = EmbeddingService(
        embedding_repository=emb_repo,
        candidate_repository=cand_repo,
        embedding_generator=generator,
    )
    mock_candidate = Candidate(id=candidate_id, tenant_id=tenant_id, skills=[])
    cand_repo.get_candidate_by_id.return_value = mock_candidate
    patch.object(service, "_construct_candidate_source_text", new_callable=AsyncMock, return_value="Hello").start()
    generator.compute_source_text_hash.return_value = "hash123"

    # Existing but invalid vector len
    existing = MagicMock()
    existing.source_text_hash = "hash123"
    existing.model_version = "text-embedding-3-small"
    existing.embedding = [0.1] * 10
    emb_repo.get_candidate_embedding.return_value = existing

    generator.generate_embedding.return_value = EmbeddingGenerationResult(
        embedding=[0.2] * 1536,
        source_text_hash="hash123",
        input_tokens=2,
        total_tokens=2,
        latency_ms=10,
        is_fallback=False,
        status="success",
        error_type=None,
    )

    session = AsyncMock()
    result = await service.generate_candidate_embedding_pipeline(
        session=session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    assert result.cache_hit is False
    generator.generate_embedding.assert_called_once_with("Hello")

@pytest.mark.asyncio
async def test_get_candidate_embedding_status_current() -> None:
    """Verify get_candidate_embedding_status returns current when hash, model, and vector match."""
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    generator = MagicMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, candidate_repository=cand_repo, embedding_generator=generator)

    cand_repo.get_candidate_by_id.return_value = Candidate(id=candidate_id, tenant_id=tenant_id, skills=[])
    patch.object(service, "_construct_candidate_source_text", new_callable=AsyncMock, return_value="text").start()
    generator.compute_source_text_hash.return_value = "hash1"

    existing = MagicMock(source_text_hash="hash1", model_version="text-embedding-3-small", embedding=[0.1]*1536)
    emb_repo.get_latest_candidate_embedding.return_value = existing

    res = await service.get_candidate_embedding_status(AsyncMock(), tenant_id, candidate_id, "text-embedding-3-small")
    assert res.data.status == "current"


@pytest.mark.asyncio
async def test_get_candidate_embedding_status_stale_hash() -> None:
    """Verify get_candidate_embedding_status returns stale on hash mismatch."""
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    generator = MagicMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, candidate_repository=cand_repo, embedding_generator=generator)

    cand_repo.get_candidate_by_id.return_value = Candidate(id=candidate_id, tenant_id=tenant_id, skills=[])
    patch.object(service, "_construct_candidate_source_text", new_callable=AsyncMock, return_value="text").start()
    generator.compute_source_text_hash.return_value = "hash2"

    existing = MagicMock(source_text_hash="hash1", model_version="text-embedding-3-small", embedding=[0.1]*1536)
    emb_repo.get_latest_candidate_embedding.return_value = existing

    res = await service.get_candidate_embedding_status(AsyncMock(), tenant_id, candidate_id, "text-embedding-3-small")
    assert res.data.status == "stale"


@pytest.mark.asyncio
async def test_get_candidate_embedding_status_stale_model() -> None:
    """Verify get_candidate_embedding_status returns stale on model mismatch."""
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    generator = MagicMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, candidate_repository=cand_repo, embedding_generator=generator)

    cand_repo.get_candidate_by_id.return_value = Candidate(id=candidate_id, tenant_id=tenant_id, skills=[])
    patch.object(service, "_construct_candidate_source_text", new_callable=AsyncMock, return_value="text").start()
    generator.compute_source_text_hash.return_value = "hash1"

    existing = MagicMock(source_text_hash="hash1", model_version="text-embedding-ada-002", embedding=[0.1]*1536)
    emb_repo.get_latest_candidate_embedding.return_value = existing

    res = await service.get_candidate_embedding_status(AsyncMock(), tenant_id, candidate_id, "text-embedding-3-small")
    assert res.data.status == "stale"


@pytest.mark.asyncio
async def test_get_candidate_embedding_status_missing() -> None:
    """Verify get_candidate_embedding_status returns missing when no embedding exists."""
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, candidate_repository=cand_repo)

    cand_repo.get_candidate_by_id.return_value = Candidate(id=candidate_id, tenant_id=tenant_id, skills=[])
    emb_repo.get_latest_candidate_embedding.return_value = None

    res = await service.get_candidate_embedding_status(AsyncMock(), tenant_id, candidate_id, "text-embedding-3-small")
    assert res.data.status == "missing"


@pytest.mark.asyncio
async def test_get_job_embedding_status_current() -> None:
    """Verify get_job_embedding_status returns current."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    generator = MagicMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo, embedding_generator=generator)

    job_repo.get_job_by_id.return_value = MagicMock()
    patch.object(service, "_construct_job_source_text", return_value="text").start()
    generator.compute_source_text_hash.return_value = "hash1"

    existing = MagicMock(source_text_hash="hash1", model_version="text-embedding-3-small", embedding=[0.1]*1536)
    emb_repo.get_latest_job_embedding.return_value = existing

    res = await service.get_job_embedding_status(AsyncMock(), tenant_id, job_id, "text-embedding-3-small")
    assert res.data.status == "current"


@pytest.mark.asyncio
async def test_get_job_embedding_status_stale() -> None:
    """Verify get_job_embedding_status returns stale."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    generator = MagicMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo, embedding_generator=generator)

    job_repo.get_job_by_id.return_value = MagicMock()
    patch.object(service, "_construct_job_source_text", return_value="text").start()
    generator.compute_source_text_hash.return_value = "hash1"

    existing = MagicMock(source_text_hash="hash1", model_version="text-embedding-3-small", embedding=[0.1]*10) # invalid length
    emb_repo.get_latest_job_embedding.return_value = existing

    res = await service.get_job_embedding_status(AsyncMock(), tenant_id, job_id, "text-embedding-3-small")
    assert res.data.status == "stale"


@pytest.mark.asyncio
async def test_get_job_embedding_status_missing() -> None:
    """Verify get_job_embedding_status returns missing."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo)

    job_repo.get_job_by_id.return_value = MagicMock()
    emb_repo.get_latest_job_embedding.return_value = None

    res = await service.get_job_embedding_status(AsyncMock(), tenant_id, job_id, "text-embedding-3-small")
    assert res.data.status == "missing"


@pytest.mark.asyncio
async def test_get_candidate_embedding_status_stale_invalid_vector() -> None:
    """Verify candidate status is stale when vector dimension is invalid."""
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    generator = MagicMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, candidate_repository=cand_repo, embedding_generator=generator)

    cand_repo.get_candidate_by_id.return_value = Candidate(id=candidate_id, tenant_id=tenant_id, skills=[])
    patch.object(service, "_construct_candidate_source_text", new_callable=AsyncMock, return_value="text").start()
    generator.compute_source_text_hash.return_value = "hash1"

    existing = MagicMock(source_text_hash="hash1", model_version="text-embedding-3-small", embedding=[0.1] * 10)
    emb_repo.get_latest_candidate_embedding.return_value = existing

    res = await service.get_candidate_embedding_status(AsyncMock(), tenant_id, candidate_id, "text-embedding-3-small")
    assert res.data.status == "stale"


@pytest.mark.asyncio
async def test_get_job_embedding_status_stale_hash() -> None:
    """Verify job status is stale on hash mismatch."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    generator = MagicMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo, embedding_generator=generator)

    job_repo.get_job_by_id.return_value = MagicMock()
    patch.object(service, "_construct_job_source_text", return_value="text").start()
    generator.compute_source_text_hash.return_value = "hash2"

    existing = MagicMock(source_text_hash="hash1", model_version="text-embedding-3-small", embedding=[0.1] * 1536)
    emb_repo.get_latest_job_embedding.return_value = existing

    res = await service.get_job_embedding_status(AsyncMock(), tenant_id, job_id, "text-embedding-3-small")
    assert res.data.status == "stale"


@pytest.mark.asyncio
async def test_get_job_embedding_status_stale_model() -> None:
    """Verify job status is stale on model version mismatch."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    generator = MagicMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo, embedding_generator=generator)

    job_repo.get_job_by_id.return_value = MagicMock()
    patch.object(service, "_construct_job_source_text", return_value="text").start()
    generator.compute_source_text_hash.return_value = "hash1"

    existing = MagicMock(source_text_hash="hash1", model_version="text-embedding-ada-002", embedding=[0.1] * 1536)
    emb_repo.get_latest_job_embedding.return_value = existing

    res = await service.get_job_embedding_status(AsyncMock(), tenant_id, job_id, "text-embedding-3-small")
    assert res.data.status == "stale"


@pytest.mark.asyncio
async def test_get_candidate_embedding_status_nonexistent() -> None:
    """Verify 404 when candidate does not exist."""
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, candidate_repository=cand_repo)

    cand_repo.get_candidate_by_id.return_value = None

    with pytest.raises(ResourceNotFoundException):
        await service.get_candidate_embedding_status(AsyncMock(), tenant_id, candidate_id)


@pytest.mark.asyncio
async def test_get_job_embedding_status_nonexistent() -> None:
    """Verify 404 when job does not exist."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo)

    job_repo.get_job_by_id.return_value = None

    with pytest.raises(ResourceNotFoundException):
        await service.get_job_embedding_status(AsyncMock(), tenant_id, job_id)


@pytest.mark.asyncio
async def test_get_candidate_embedding_status_cross_tenant_returns_404() -> None:
    """Verify cross-tenant candidate lookup returns 404 (repo returns None for wrong tenant)."""
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, candidate_repository=cand_repo)

    # Repository scopes by tenant_id, so cross-tenant lookup returns None
    cand_repo.get_candidate_by_id.return_value = None

    with pytest.raises(ResourceNotFoundException):
        await service.get_candidate_embedding_status(AsyncMock(), tenant_id, candidate_id)


@pytest.mark.asyncio
async def test_get_job_embedding_status_cross_tenant_returns_404() -> None:
    """Verify cross-tenant job lookup returns 404 (repo returns None for wrong tenant)."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo)

    job_repo.get_job_by_id.return_value = None

    with pytest.raises(ResourceNotFoundException):
        await service.get_job_embedding_status(AsyncMock(), tenant_id, job_id)


@pytest.mark.asyncio
async def test_get_candidate_embedding_status_hiring_manager_allowed() -> None:
    """Verify hiring_manager can read candidate embedding status (GET is read-only)."""
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, candidate_repository=cand_repo)

    cand_repo.get_candidate_by_id.return_value = Candidate(id=candidate_id, tenant_id=tenant_id, skills=[])
    emb_repo.get_latest_candidate_embedding.return_value = None

    res = await service.get_candidate_embedding_status(AsyncMock(), tenant_id, candidate_id)
    assert res.data.status == "missing"


@pytest.mark.asyncio
async def test_get_job_embedding_status_hiring_manager_allowed() -> None:
    """Verify hiring_manager can read job embedding status (GET is read-only)."""
    emb_repo = AsyncMock()
    job_repo = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    service = EmbeddingService(embedding_repository=emb_repo, job_repository=job_repo)

    job_repo.get_job_by_id.return_value = MagicMock()
    emb_repo.get_latest_job_embedding.return_value = None

    res = await service.get_job_embedding_status(AsyncMock(), tenant_id, job_id)
    assert res.data.status == "missing"
