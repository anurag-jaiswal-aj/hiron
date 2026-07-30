"""Unit tests for CandidateRepository database operations."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from hiron.candidates.models import Candidate, JobCandidate
from hiron.candidates.repository import CandidateRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_candidate_success(mock_session: AsyncMock) -> None:
    """Verify CandidateRepository.create_candidate adds record and flushes session."""
    tenant_id = uuid.uuid4()
    candidate = Candidate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        full_name="Alice Smith",
        email="alice@example.com",
    )

    repo = CandidateRepository()
    result = await repo.create_candidate(mock_session, candidate)

    assert result.full_name == "Alice Smith"
    mock_session.add.assert_called_once_with(candidate)
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_candidate_by_id_success(mock_session: AsyncMock) -> None:
    """Verify get_candidate_by_id executes query and returns candidate."""
    candidate_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    candidate = Candidate(id=candidate_id, tenant_id=tenant_id, full_name="Bob Jones")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = candidate
    mock_session.execute.return_value = mock_result

    repo = CandidateRepository()
    result = await repo.get_candidate_by_id(mock_session, candidate_id, tenant_id)

    assert result is not None
    assert result.id == candidate_id
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_candidate_to_job_success(mock_session: AsyncMock) -> None:
    """Verify add_candidate_to_job adds JobCandidate record and flushes."""
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    stage_id = uuid.uuid4()

    assoc = JobCandidate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        candidate_id=candidate_id,
        current_stage_id=stage_id,
    )

    mock_result = MagicMock()
    mock_result.scalar_one.return_value = assoc
    mock_session.execute.return_value = mock_result

    repo = CandidateRepository()
    result = await repo.add_candidate_to_job(mock_session, assoc)

    assert result == assoc
    mock_session.add.assert_called_once_with(assoc)
    mock_session.flush.assert_awaited_once()
