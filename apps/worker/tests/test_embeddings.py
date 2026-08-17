import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apps.worker.src.embeddings import (
    generate_candidate_embedding_worker_pipeline,
    generate_job_embedding_worker_pipeline,
)
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.candidates.models import Candidate
from hiron.embeddings.generator import EMBEDDING_DIMENSION, EmbeddingGenerationResult


@pytest.fixture
def mock_session():
    session = AsyncMock(spec=AsyncSession)
    session.begin_nested = MagicMock()
    session.begin_nested.return_value = AsyncMock()
    return session


@pytest.mark.asyncio
@patch("hiron.embeddings.service.CandidateRepository")
@patch("hiron.embeddings.service.EmbeddingRepository")
@patch("hiron.embeddings.service.EmbeddingGenerator")
@patch("apps.worker.src.embeddings.AIUsageRepository")
@patch("hiron.embeddings.service.EmbeddingService._construct_candidate_source_text")
async def test_generate_candidate_embedding_worker_pipeline_success(
    mock_construct_text,
    mock_ai_repo_cls,
    mock_gen_cls,
    mock_emb_repo_cls,
    mock_cand_repo_cls,
    mock_session,
):
    """Test candidate embedding generation and telemetry logging."""
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_cand_repo = mock_cand_repo_cls.return_value
    mock_emb_repo = mock_emb_repo_cls.return_value
    mock_gen = mock_gen_cls.return_value
    mock_ai_repo = mock_ai_repo_cls.return_value

    # 1. Candidate text retrieval
    mock_candidate = Candidate(id=candidate_id, tenant_id=tenant_id, skills=["Python"])
    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=mock_candidate)
    mock_construct_text.return_value = "Python Developer"

    # Hash computation
    mock_gen.compute_source_text_hash.return_value = "hash123"

    # Cache miss
    mock_emb_repo.get_candidate_embedding = AsyncMock(return_value=None)
    mock_emb_repo.upsert_candidate_embedding = AsyncMock()
    mock_ai_repo.create_usage_log = AsyncMock()

    # 2 & 3. Gemini generation with correct dimensions
    valid_embedding = [0.1] * EMBEDDING_DIMENSION
    mock_gen.generate_embedding = AsyncMock(return_value=EmbeddingGenerationResult(
        embedding=valid_embedding,
        source_text_hash="hash123",
        input_tokens=100,
        total_tokens=100,
        latency_ms=250,
        is_fallback=False,
        status="success",
        error_type=None,
    ))

    await generate_candidate_embedding_worker_pipeline(
        session=mock_session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    # 4 & 5. Upsert CandidateEmbedding
    mock_emb_repo.upsert_candidate_embedding.assert_called_once_with(
        session=mock_session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        embedding=valid_embedding,
        model_version="gemini-embedding-2",
        source_text_hash="hash123",
    )

    # 15. Telemetry
    mock_ai_repo.create_usage_log.assert_called_once_with(
        session=mock_session,
        tenant_id=tenant_id,
        operation="generate_candidate_embedding",
        model_version="gemini-embedding-2",
        input_tokens=100,
        output_tokens=0,
        cost_usd=2e-06,
        latency_ms=250,
        status="success",
        error_type=None,
        is_cache_hit=False,
    )

    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("hiron.embeddings.service.CandidateRepository")
@patch("hiron.embeddings.service.EmbeddingRepository")
@patch("hiron.embeddings.service.EmbeddingGenerator")
@patch("apps.worker.src.embeddings.AIUsageRepository")
@patch("hiron.embeddings.service.EmbeddingService._construct_candidate_source_text")
async def test_generate_candidate_embedding_worker_pipeline_cache_hit(
    mock_construct_text,
    mock_ai_repo_cls,
    mock_gen_cls,
    mock_emb_repo_cls,
    mock_cand_repo_cls,
    mock_session,
):
    """Test cache hit skips generation but logs telemetry."""
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_cand_repo = mock_cand_repo_cls.return_value
    mock_emb_repo = mock_emb_repo_cls.return_value
    mock_gen = mock_gen_cls.return_value
    mock_ai_repo = mock_ai_repo_cls.return_value

    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=Candidate(
        id=candidate_id, tenant_id=tenant_id
    ))
    mock_construct_text.return_value = "Python Developer"
    mock_gen.compute_source_text_hash.return_value = "hash123"

    # 6. Cache hit
    mock_existing = MagicMock(
        source_text_hash="hash123",
        model_version="gemini-embedding-2",
        embedding=[0.1] * EMBEDDING_DIMENSION,
    )
    mock_emb_repo.get_candidate_embedding = AsyncMock(return_value=mock_existing)
    mock_ai_repo.create_usage_log = AsyncMock()

    await generate_candidate_embedding_worker_pipeline(
        session=mock_session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
    )

    # Generation and upsert skipped
    mock_gen.generate_embedding.assert_not_called()
    mock_emb_repo.upsert_candidate_embedding.assert_not_called()

    # Telemetry logged as cache hit
    mock_ai_repo.create_usage_log.assert_called_once_with(
        session=mock_session,
        tenant_id=tenant_id,
        operation="generate_candidate_embedding",
        model_version="gemini-embedding-2",
        input_tokens=0,
        output_tokens=0,
        cost_usd=0.0,
        latency_ms=0,
        status="success",
        error_type=None,
        is_cache_hit=True,
    )

    mock_session.commit.assert_called_once()


@pytest.mark.asyncio
@patch("hiron.embeddings.service.CandidateRepository")
@patch("hiron.embeddings.service.EmbeddingRepository")
@patch("hiron.embeddings.service.EmbeddingGenerator")
@patch("apps.worker.src.embeddings.AIUsageRepository")
@patch("hiron.embeddings.service.EmbeddingService._construct_candidate_source_text")
async def test_generate_candidate_embedding_worker_pipeline_gemini_failure_propagates(
    mock_construct_text,
    mock_ai_repo_cls,
    mock_gen_cls,
    mock_emb_repo_cls,
    mock_cand_repo_cls,
    mock_session,
):
    """Test Gemini exception propagates upwards without being swallowed."""
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_cand_repo = mock_cand_repo_cls.return_value
    mock_emb_repo = mock_emb_repo_cls.return_value
    mock_gen = mock_gen_cls.return_value
    mock_ai_repo = mock_ai_repo_cls.return_value

    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=Candidate(
        id=candidate_id, tenant_id=tenant_id
    ))
    mock_construct_text.return_value = "Python Developer"
    mock_gen.compute_source_text_hash.return_value = "hash123"
    mock_emb_repo.get_candidate_embedding = AsyncMock(return_value=None)
    mock_emb_repo.upsert_candidate_embedding = AsyncMock()
    mock_ai_repo.create_usage_log = AsyncMock()

    # 11. Gemini exception
    class GeminiError(Exception):
        pass

    mock_gen.generate_embedding = AsyncMock(side_effect=GeminiError("API failure"))

    with pytest.raises(GeminiError):
        await generate_candidate_embedding_worker_pipeline(
            session=mock_session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
        )

    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
@patch("hiron.embeddings.service.CandidateRepository")
@patch("hiron.embeddings.service.EmbeddingRepository")
@patch("hiron.embeddings.service.EmbeddingGenerator")
@patch("apps.worker.src.embeddings.AIUsageRepository")
@patch("hiron.embeddings.service.EmbeddingService._construct_candidate_source_text")
async def test_generate_candidate_embedding_worker_pipeline_db_failure_propagates(
    mock_construct_text,
    mock_ai_repo_cls,
    mock_gen_cls,
    mock_emb_repo_cls,
    mock_cand_repo_cls,
    mock_session,
):
    """Test Database exception propagates upwards without being swallowed."""
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_cand_repo = mock_cand_repo_cls.return_value
    mock_emb_repo = mock_emb_repo_cls.return_value
    mock_gen = mock_gen_cls.return_value
    mock_ai_repo = mock_ai_repo_cls.return_value

    mock_cand_repo.get_candidate_by_id = AsyncMock(return_value=Candidate(
        id=candidate_id, tenant_id=tenant_id
    ))
    mock_construct_text.return_value = "Python Developer"
    mock_gen.compute_source_text_hash.return_value = "hash123"
    mock_emb_repo.get_candidate_embedding = AsyncMock(return_value=None)
    mock_emb_repo.upsert_candidate_embedding = AsyncMock()
    mock_ai_repo.create_usage_log = AsyncMock()

    mock_gen.generate_embedding = AsyncMock(return_value=EmbeddingGenerationResult(
        embedding=[0.1] * EMBEDDING_DIMENSION,
        source_text_hash="hash123",
        input_tokens=100,
        total_tokens=100,
        latency_ms=250,
        is_fallback=False,
        status="success",
        error_type=None,
    ))

    # 12. Database exception on upsert
    class DBError(Exception):
        pass

    mock_emb_repo.upsert_candidate_embedding = AsyncMock(side_effect=DBError("DB failure"))

    with pytest.raises(DBError):
        await generate_candidate_embedding_worker_pipeline(
            session=mock_session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
        )

    mock_session.commit.assert_not_called()


@pytest.mark.asyncio
@patch("hiron.embeddings.service.JobRepository")
@patch("hiron.embeddings.service.EmbeddingRepository")
@patch("hiron.embeddings.service.EmbeddingGenerator")
@patch("apps.worker.src.embeddings.AIUsageRepository")
@patch("hiron.embeddings.service.EmbeddingService._construct_job_source_text")
async def test_generate_job_embedding_worker_pipeline_success(
    mock_construct_text,
    mock_ai_repo_cls,
    mock_gen_cls,
    mock_emb_repo_cls,
    mock_job_repo_cls,
    mock_session,
):
    """Test job embedding generation and telemetry logging."""
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    mock_job_repo = mock_job_repo_cls.return_value
    mock_emb_repo = mock_emb_repo_cls.return_value
    mock_gen = mock_gen_cls.return_value
    mock_ai_repo = mock_ai_repo_cls.return_value

    mock_job_repo.get_job_by_id = AsyncMock(return_value=MagicMock(id=job_id, tenant_id=tenant_id))
    mock_construct_text.return_value = "Backend Engineer"
    mock_gen.compute_source_text_hash.return_value = "hash456"
    mock_emb_repo.get_job_embedding = AsyncMock(return_value=None)
    mock_emb_repo.upsert_job_embedding = AsyncMock()
    mock_ai_repo.create_usage_log = AsyncMock()

    valid_embedding = [0.2] * EMBEDDING_DIMENSION
    mock_gen.generate_embedding = AsyncMock(return_value=EmbeddingGenerationResult(
        embedding=valid_embedding,
        source_text_hash="hash456",
        input_tokens=50,
        total_tokens=50,
        latency_ms=150,
        is_fallback=False,
        status="success",
        error_type=None,
    ))

    await generate_job_embedding_worker_pipeline(
        session=mock_session,
        tenant_id=tenant_id,
        job_id=job_id,
    )

    mock_emb_repo.upsert_job_embedding.assert_called_once_with(
        session=mock_session,
        tenant_id=tenant_id,
        job_id=job_id,
        embedding=valid_embedding,
        model_version="gemini-embedding-2",
        source_text_hash="hash456",
    )

    mock_ai_repo.create_usage_log.assert_called_once_with(
        session=mock_session,
        tenant_id=tenant_id,
        operation="generate_job_embedding",
        model_version="gemini-embedding-2",
        input_tokens=50,
        output_tokens=0,
        cost_usd=1e-06,
        latency_ms=150,
        status="success",
        error_type=None,
        is_cache_hit=False,
    )

    mock_session.commit.assert_called_once()

@pytest.mark.asyncio
@patch("hiron.embeddings.generator.get_settings")
@patch("google.genai.Client")
async def test_embedding_token_accounting_failure(mock_genai_client, mock_get_settings):
    """Test that a failure in count_tokens does not produce a fake $0 successful usage record."""
    mock_settings = MagicMock()
    mock_settings.is_production = True
    mock_get_settings.return_value = mock_settings

    mock_client_instance = MagicMock()
    mock_genai_client.return_value = mock_client_instance
    mock_client_instance.aio.models.embed_content = AsyncMock(return_value=MagicMock(
        embeddings=[MagicMock(values=[0.1] * EMBEDDING_DIMENSION)]
    ))

    # Simulate token counting failure
    class TokenCountingError(Exception):
        pass
    mock_client_instance.aio.models.count_tokens = AsyncMock(side_effect=TokenCountingError("Network error"))

    from hiron.embeddings.generator import EmbeddingGenerator
    generator = EmbeddingGenerator()
    generator.gemini_api_key = "dummy"

    # In production, the exception bubbles up, failing the entire operation.
    with pytest.raises(TokenCountingError):
        await generator.generate_embedding("Test text")
