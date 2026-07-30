"""Unit tests for PipelineRepository stage movements, history audit logging, and Kanban board queries."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.candidates.models import JobCandidate
from hiron.pipeline.repository import PipelineRepository


@pytest.mark.asyncio
async def test_create_stage_history_inserts_record() -> None:
    """Verify create_stage_history adds CandidateStageHistory entity."""
    repo = PipelineRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_cand_id = uuid.uuid4()
    from_stage_id = uuid.uuid4()
    to_stage_id = uuid.uuid4()
    user_id = uuid.uuid4()

    history = await repo.create_stage_history(
        session=session,
        tenant_id=tenant_id,
        job_candidate_id=job_cand_id,
        from_stage_id=from_stage_id,
        to_stage_id=to_stage_id,
        moved_by=user_id,
        note="Moving to phone screen",
    )

    assert history.tenant_id == tenant_id
    assert history.job_candidate_id == job_cand_id
    assert history.from_stage_id == from_stage_id
    assert history.to_stage_id == to_stage_id
    assert history.note == "Moving to phone screen"
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_update_job_candidate_stage() -> None:
    """Verify update_job_candidate_stage updates current_stage_id."""
    repo = PipelineRepository()
    session = AsyncMock()
    job_candidate = JobCandidate(id=uuid.uuid4(), current_stage_id=uuid.uuid4())
    new_stage_id = uuid.uuid4()

    updated = await repo.update_job_candidate_stage(session, job_candidate, new_stage_id)

    assert updated.current_stage_id == new_stage_id
    session.flush.assert_called_once()
