"""Service unit tests for candidate/job embedding generation, staleness detection, and RBAC validation."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.candidates.models import Candidate
from hiron.common.exceptions import ResourceNotFoundException
from hiron.embeddings.exceptions import InsufficientEmbeddingPermissionsError
from hiron.embeddings.service import EmbeddingService


@pytest.mark.asyncio
async def test_generate_candidate_embedding_success() -> None:
    """Verify generate_candidate_embedding executes pipeline and returns 202 response schema."""
    emb_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()
    generator = AsyncMock()

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

    mock_resume_result = AsyncMock()
    mock_resume_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_resume_result

    response = await service.generate_candidate_embedding(
        session=session,
        tenant_id=tenant_id,
        user_role="recruiter",
        candidate_id=candidate_id,
    )

    assert response.data.candidate_id == candidate_id
    assert response.data.status == "processing"
    assert response.data.model_version == "text-embedding-3-small"
    emb_repo.upsert_candidate_embedding.assert_called_once()


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
