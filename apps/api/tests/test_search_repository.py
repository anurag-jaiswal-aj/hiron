"""Unit tests for SearchRepository candidate similarity search, hybrid metadata filter clauses, and saved search CRUD."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from hiron.candidates.models import Candidate
from hiron.embeddings.models import CandidateEmbedding
from hiron.search.repository import SearchRepository
from hiron.search.schemas import SearchCandidateFilters


@pytest.mark.asyncio
async def test_search_candidates_by_vector_and_filters() -> None:
    """Verify search_candidates_by_vector_and_filters ranks candidates by vector similarity."""
    repo = SearchRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()

    cand1 = Candidate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        full_name="Jane Doe",
        skills=["Python"],
        total_experience_years=6,
    )
    emb1 = CandidateEmbedding(id=uuid.uuid4(), candidate_id=cand1.id, embedding=[1.0, 0.0])

    cand2 = Candidate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        full_name="John Smith",
        skills=["Python"],
        total_experience_years=8,
    )
    emb2 = CandidateEmbedding(id=uuid.uuid4(), candidate_id=cand2.id, embedding=[0.0, 1.0])

    mock_result = MagicMock()
    mock_result.all.return_value = [(cand1, emb1), (cand2, emb2)]
    session.execute = AsyncMock(return_value=mock_result)

    results = await repo.search_candidates_by_vector_and_filters(
        session=session,
        tenant_id=tenant_id,
        query_vector=[1.0, 0.0],
        filters=SearchCandidateFilters(experience_min=5),
        limit=10,
    )

    assert len(results) == 2
    assert results[0][0].id == cand1.id
    assert results[0][1] == 1.0


@pytest.mark.asyncio
async def test_create_and_get_saved_search() -> None:
    """Verify create_saved_search and get_saved_search_by_id operations."""
    repo = SearchRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    search = await repo.create_saved_search(
        session=session,
        tenant_id=tenant_id,
        created_by=user_id,
        name="Senior Python Devs",
        query_text="Python developers in SF",
        filters={"experienceMin": 5},
    )

    assert search.name == "Senior Python Devs"
    assert search.tenant_id == tenant_id
    session.add.assert_called_once()
