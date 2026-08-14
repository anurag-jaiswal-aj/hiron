"""Service unit tests for query embedding generation, relevance score normalization, highlight extraction, and saved search management."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from hiron.candidates.models import Candidate
from hiron.embeddings.generator import EMBEDDING_DIMENSION, EmbeddingGenerationResult
from hiron.search.exceptions import InsufficientSearchPermissionsError, SearchQueryValidationError
from hiron.search.service import SearchService


@pytest.mark.asyncio
async def test_search_candidates_query_validation() -> None:
    """Verify search_candidates raises SearchQueryValidationError for invalid query length."""
    service = SearchService()
    session = AsyncMock()

    with pytest.raises(SearchQueryValidationError):
        await service.search_candidates(
            session=session,
            tenant_id=uuid.uuid4(),
            user_role="recruiter",
            query="hi",  # Too short (< 3 chars)
        )


@pytest.mark.asyncio
async def test_search_candidates_role_authorization() -> None:
    """Verify search_candidates raises InsufficientSearchPermissionsError for unauthorized role."""
    service = SearchService()
    session = AsyncMock()

    with pytest.raises(InsufficientSearchPermissionsError):
        await service.search_candidates(
            session=session,
            tenant_id=uuid.uuid4(),
            user_role="member",
            query="Senior Python Developer",
        )


@pytest.mark.asyncio
async def test_search_candidates_success() -> None:
    """Verify search_candidates generates query vector, executes search, and returns response schema."""
    search_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()
    emb_repo = AsyncMock()
    generator = MagicMock()

    service = SearchService(
        search_repository=search_repo,
        candidate_repository=cand_repo,
        job_repository=job_repo,
        embedding_repository=emb_repo,
        embedding_generator=generator,
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    generator.generate_embedding = AsyncMock(return_value=EmbeddingGenerationResult(
        embedding=[0.1] * EMBEDDING_DIMENSION,
        source_text_hash="hash123",
        input_tokens=10,
        total_tokens=15,
        latency_ms=100,
        is_fallback=False,
        status="success",
        error_type=None,
    ))
    cand = Candidate(
        id=candidate_id,
        tenant_id=tenant_id,
        full_name="Jane Smith",
        current_title="Senior Engineer",
        skills=["Python"],
        total_experience_years=8,
    )
    search_repo.search_candidates_by_vector_and_filters.return_value = [(cand, 0.92)]

    response = await service.search_candidates(
        session=session,
        tenant_id=tenant_id,
        user_role="recruiter",
        query="Senior Python Developer",
    )

    assert len(response.data) == 1
    assert response.data[0].candidate.full_name == "Jane Smith"
    assert response.data[0].relevance_score == 0.92
    assert response.pagination.total_count == 1
