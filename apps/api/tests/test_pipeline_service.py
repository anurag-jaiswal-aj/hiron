"""Service unit tests for stage validation, same-stage no-op protection, Hiring Manager RBAC restriction, and timeline retrieval."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.candidates.models import JobCandidate
from hiron.jobs.models import PipelineStage
from hiron.pipeline.exceptions import (
    InsufficientPipelinePermissionsError,
    PipelineStageValidationError,
)
from hiron.pipeline.service import PipelineService


@pytest.mark.asyncio
async def test_hiring_manager_move_candidate_raises_403() -> None:
    """Verify hiring_manager role cannot move candidate stages (read-only in pipeline)."""
    service = PipelineService()
    session = AsyncMock()

    with pytest.raises(InsufficientPipelinePermissionsError):
        await service.move_candidate_stage(
            session=session,
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_role="hiring_manager",
            job_candidate_id=uuid.uuid4(),
            to_stage_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_move_candidate_same_stage_raises_validation_error() -> None:
    """Verify moving candidate to their current stage raises PipelineStageValidationError (no-op protection)."""
    pipe_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()
    user_repo = AsyncMock()

    service = PipelineService(
        pipeline_repository=pipe_repo,
        candidate_repository=cand_repo,
        job_repository=job_repo,
        user_repository=user_repo,
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    stage_id = uuid.uuid4()

    mock_stage = PipelineStage(
        id=stage_id, tenant_id=tenant_id, job_id=job_id, name="Screening", position=2
    )
    mock_jc = JobCandidate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job_id,
        current_stage_id=stage_id,
        current_stage=mock_stage,
    )

    pipe_repo.get_job_candidate_by_id.return_value = mock_jc
    pipe_repo.get_stage_by_id.return_value = mock_stage

    with pytest.raises(
        PipelineStageValidationError, match="already in the requested pipeline stage"
    ):
        await service.move_candidate_stage(
            session=session,
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            user_role="recruiter",
            job_candidate_id=mock_jc.id,
            to_stage_id=stage_id,
        )


@pytest.mark.asyncio
async def test_move_candidate_different_job_stage_raises_validation_error() -> None:
    """Verify moving candidate to a stage belonging to a different job raises PipelineStageValidationError."""
    pipe_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()
    user_repo = AsyncMock()

    service = PipelineService(
        pipeline_repository=pipe_repo,
        candidate_repository=cand_repo,
        job_repository=job_repo,
        user_repository=user_repo,
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job1_id = uuid.uuid4()
    job2_id = uuid.uuid4()

    stage1_id = uuid.uuid4()
    stage2_id = uuid.uuid4()

    mock_stage1 = PipelineStage(
        id=stage1_id, tenant_id=tenant_id, job_id=job1_id, name="Applied", position=1
    )
    mock_stage2 = PipelineStage(
        id=stage2_id, tenant_id=tenant_id, job_id=job2_id, name="Screening", position=2
    )  # Different job!
    mock_jc = JobCandidate(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_id=job1_id,
        current_stage_id=stage1_id,
        current_stage=mock_stage1,
    )

    pipe_repo.get_job_candidate_by_id.return_value = mock_jc
    pipe_repo.get_stage_by_id.return_value = mock_stage2

    with pytest.raises(PipelineStageValidationError, match="does not belong to candidate's job"):
        await service.move_candidate_stage(
            session=session,
            tenant_id=tenant_id,
            user_id=uuid.uuid4(),
            user_role="recruiter",
            job_candidate_id=mock_jc.id,
            to_stage_id=stage2_id,
        )
