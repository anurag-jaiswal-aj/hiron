"""Unit tests for CandidateService domain logic and business rules."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.candidates.exceptions import (
    DuplicateCandidateEmailError,
    InsufficientCandidatePermissionsError,
    InvalidCandidateDataError,
    JobCandidateConflictError,
)
from hiron.candidates.models import Candidate, JobCandidate
from hiron.candidates.service import CandidateService
from hiron.jobs.models import Job, PipelineStage


@pytest.fixture
def mock_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_create_candidate_duplicate_email_raises_409(mock_session: AsyncMock) -> None:
    """Verify creating candidate with existing email in tenant raises DuplicateCandidateEmailError."""
    tenant_id = uuid.uuid4()
    existing_candidate = Candidate(id=uuid.uuid4(), tenant_id=tenant_id, email="dup@example.com")

    mock_repo = AsyncMock()
    mock_repo.get_candidate_by_email.return_value = existing_candidate

    service = CandidateService(candidate_repo=mock_repo)

    with pytest.raises(DuplicateCandidateEmailError):
        await service.create_candidate(
            session=mock_session,
            tenant_id=tenant_id,
            current_user_role="recruiter",
            full_name="Duplicate User",
            email="dup@example.com",
        )


@pytest.mark.asyncio
async def test_create_candidate_invalid_experience_raises_422(mock_session: AsyncMock) -> None:
    """Verify total experience years > 70 raises InvalidCandidateDataError."""
    tenant_id = uuid.uuid4()
    mock_repo = AsyncMock()
    service = CandidateService(candidate_repo=mock_repo)

    with pytest.raises(InvalidCandidateDataError, match="experience years"):
        await service.create_candidate(
            session=mock_session,
            tenant_id=tenant_id,
            current_user_role="recruiter",
            full_name="Invalid User",
            total_experience_years=85,
        )


@pytest.mark.asyncio
async def test_create_candidate_forbidden_role_raises_403(mock_session: AsyncMock) -> None:
    """Verify hiring manager role attempting to create candidate raises InsufficientCandidatePermissionsError."""
    tenant_id = uuid.uuid4()
    mock_repo = AsyncMock()
    service = CandidateService(candidate_repo=mock_repo)

    with pytest.raises(InsufficientCandidatePermissionsError):
        await service.create_candidate(
            session=mock_session,
            tenant_id=tenant_id,
            current_user_role="hiring_manager",
            full_name="HM User",
        )


@pytest.mark.asyncio
async def test_add_candidate_to_job_places_in_initial_stage(mock_session: AsyncMock) -> None:
    """Verify candidate added to job is automatically assigned to initial pipeline stage (position 1)."""
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    user_id = uuid.uuid4()

    candidate = Candidate(id=candidate_id, tenant_id=tenant_id, full_name="John Candidate")
    job = Job(id=job_id, tenant_id=tenant_id, title="Backend Engineer", status="open")

    stage1 = PipelineStage(
        id=uuid.uuid4(), tenant_id=tenant_id, job_id=job_id, name="Applied", position=1
    )
    stage2 = PipelineStage(
        id=uuid.uuid4(), tenant_id=tenant_id, job_id=job_id, name="Interview", position=2
    )

    created_jc = JobCandidate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        candidate_id=candidate_id,
        current_stage_id=stage1.id,
    )
    created_jc.current_stage = stage1

    mock_cand_repo = AsyncMock()
    mock_cand_repo.get_candidate_by_id.return_value = candidate
    mock_cand_repo.get_job_candidate.return_value = None
    mock_cand_repo.add_candidate_to_job.return_value = created_jc

    mock_job_repo = AsyncMock()
    mock_job_repo.get_job_by_id.return_value = job
    mock_job_repo.list_pipeline_stages.return_value = [stage2, stage1]

    service = CandidateService(candidate_repo=mock_cand_repo, job_repo=mock_job_repo)

    result = await service.add_candidate_to_job(
        session=mock_session,
        job_id=job_id,
        candidate_id=candidate_id,
        tenant_id=tenant_id,
        added_by_user_id=user_id,
        current_user_role="recruiter",
    )

    assert result.current_stage_id == stage1.id
    assert result.current_stage.name == "Applied"


@pytest.mark.asyncio
async def test_add_candidate_to_job_conflict_raises_409(mock_session: AsyncMock) -> None:
    """Verify adding an already associated candidate to a job raises JobCandidateConflictError."""
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    candidate = Candidate(id=candidate_id, tenant_id=tenant_id, full_name="John Candidate")
    job = Job(id=job_id, tenant_id=tenant_id, title="Backend Engineer", status="open")
    existing_assoc = JobCandidate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        candidate_id=candidate_id,
        current_stage_id=uuid.uuid4(),
    )

    mock_cand_repo = AsyncMock()
    mock_cand_repo.get_candidate_by_id.return_value = candidate
    mock_cand_repo.get_job_candidate.return_value = existing_assoc

    mock_job_repo = AsyncMock()
    mock_job_repo.get_job_by_id.return_value = job

    service = CandidateService(candidate_repo=mock_cand_repo, job_repo=mock_job_repo)

    with pytest.raises(JobCandidateConflictError):
        await service.add_candidate_to_job(
            session=mock_session,
            job_id=job_id,
            candidate_id=candidate_id,
            tenant_id=tenant_id,
            added_by_user_id=uuid.uuid4(),
            current_user_role="recruiter",
        )
