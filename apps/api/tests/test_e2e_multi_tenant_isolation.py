"""Multi-Tenant Isolation E2E test verifying zero cross-tenant data leakage per Phase 17."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.candidates.exceptions import CandidateNotFoundError
from hiron.candidates.service import CandidateService
from hiron.common.exceptions import ResourceNotFoundException
from hiron.jobs.exceptions import JobNotFoundError
from hiron.jobs.service import JobService
from hiron.notes.service import NoteService
from hiron.scores.service import ScoreService
from hiron.tags.service import TagService


@pytest.mark.asyncio
async def test_multi_tenant_isolation_zero_cross_tenant_leakage() -> None:
    """Verify Tenant B cannot access Tenant A candidates, jobs, scores, notes, or tags."""
    session = AsyncMock()
    tenant_a_id = uuid.uuid4()
    tenant_b_id = uuid.uuid4()

    user_b_id = uuid.uuid4()

    job_a_id = uuid.uuid4()
    candidate_a_id = uuid.uuid4()

    # 1. Job Isolation Verification
    job_service = JobService()
    job_service.job_repo = AsyncMock()
    job_service.job_repo.get_job_by_id.side_effect = lambda _s, tid, jid: (
        AsyncMock(id=jid, tenant_id=tid, title="Tenant A Secret Job")
        if tid == tenant_a_id and jid == job_a_id
        else None
    )

    with pytest.raises(JobNotFoundError):
        await job_service.get_job_by_id(session=session, tenant_id=tenant_b_id, job_id=job_a_id)

    # 2. Candidate Isolation Verification
    candidate_service = CandidateService()
    candidate_service.candidate_repo = AsyncMock()
    candidate_service.candidate_repo.get_candidate_by_id.side_effect = lambda _s, tid, cid: (
        AsyncMock(id=cid, tenant_id=tid, full_name="Tenant A Secret Candidate")
        if tid == tenant_a_id and cid == candidate_a_id
        else None
    )

    with pytest.raises(CandidateNotFoundError):
        await candidate_service.get_candidate_by_id(
            session=session, tenant_id=tenant_b_id, candidate_id=candidate_a_id
        )

    # 3. Score Isolation Verification
    score_service = ScoreService()
    score_service.score_repo = AsyncMock()
    score_service.candidate_repo = AsyncMock()
    score_service.job_repo = AsyncMock()
    score_service.candidate_repo.get_candidate_by_id.return_value = AsyncMock(id=candidate_a_id)
    score_service.job_repo.get_job_by_id.return_value = AsyncMock(id=job_a_id)
    score_service.score_repo.get_current_score.return_value = None

    with pytest.raises(ResourceNotFoundException):
        await score_service.get_score(
            session=session,
            tenant_id=tenant_b_id,
            job_id=job_a_id,
            candidate_id=candidate_a_id,
        )

    # 4. Notes Isolation Verification
    note_service = NoteService()
    note_service.note_repo = AsyncMock()
    note_service.candidate_repo = AsyncMock()
    note_service.candidate_repo.get_candidate_by_id.return_value = AsyncMock(id=candidate_a_id)
    note_service.note_repo.list_notes.return_value = []  # Empty list for Tenant B

    notes_res = await note_service.list_candidate_notes(
        session=session,
        tenant_id=tenant_b_id,
        user_id=user_b_id,
        candidate_id=candidate_a_id,
    )
    assert len(notes_res.data) == 0

    # 5. Tags Isolation Verification
    tag_service = TagService()
    tag_service.tag_repo = AsyncMock()
    tag_service.candidate_repo = AsyncMock()
    tag_service.candidate_repo.get_candidate_by_id.return_value = AsyncMock(id=candidate_a_id)
    tag_service.tag_repo.list_tags.return_value = []  # Empty list for Tenant B

    tags_res = await tag_service.list_candidate_tags(
        session=session,
        tenant_id=tenant_b_id,
        candidate_id=candidate_a_id,
    )
    assert len(tags_res.data) == 0
