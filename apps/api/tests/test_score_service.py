"""Service unit tests for candidate scoring, 24h idempotency caching, batch scoring, and RBAC validation."""

import datetime
import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.candidates.models import Candidate, JobCandidate
from hiron.jobs.models import Job
from hiron.scores.exceptions import InsufficientScorePermissionsError
from hiron.scores.models import Score
from hiron.scores.service import ScoreService


@pytest.mark.asyncio
async def test_score_candidate_sync_success() -> None:
    """Verify score_candidate_sync runs scoring engine and saves new score."""
    score_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()
    emb_repo = AsyncMock()

    service = ScoreService(
        score_repository=score_repo,
        candidate_repository=cand_repo,
        job_repository=job_repo,
        embedding_repository=emb_repo,
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    job_cand_id = uuid.uuid4()

    cand_repo.get_candidate_by_id.return_value = Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="Jane Doe"
    )
    job_repo.get_job_by_id.return_value = Job(
        id=job_id, tenant_id=tenant_id, title="Backend Dev", description="Python"
    )
    cand_repo.get_job_candidate.return_value = JobCandidate(
        id=job_cand_id, tenant_id=tenant_id, job_id=job_id, candidate_id=candidate_id
    )
    score_repo.get_current_score.return_value = None

    mock_new_score = Score(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_candidate_id=job_cand_id,
        fit_score=85,
        confidence=0.85,
        breakdown={},
        explanation="Good match",
        skills_matched=["Python"],
        skills_missing=[],
        prompt_name="candidate_fit_scoring",
        prompt_version="2.0.0",
        model_version="gpt-4o-2024-08-06",
        is_current=True,
        created_at=datetime.datetime.now(datetime.UTC),
    )
    score_repo.create_score.return_value = mock_new_score

    response = await service.score_candidate_sync(
        session=session,
        tenant_id=tenant_id,
        user_role="recruiter",
        job_id=job_id,
        candidate_id=candidate_id,
    )

    assert response.data.fit_score == 85
    score_repo.create_score.assert_called_once()


@pytest.mark.asyncio
async def test_score_candidate_sync_idempotent_cached_response() -> None:
    """Verify score_candidate_sync returns cached score within 24h when force_rescore=False."""
    score_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()

    service = ScoreService(
        score_repository=score_repo,
        candidate_repository=cand_repo,
        job_repository=job_repo,
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    job_cand_id = uuid.uuid4()

    cand_repo.get_candidate_by_id.return_value = Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="Jane Doe"
    )
    job_repo.get_job_by_id.return_value = Job(id=job_id, tenant_id=tenant_id, title="Backend Dev")
    cand_repo.get_job_candidate.return_value = JobCandidate(
        id=job_cand_id, tenant_id=tenant_id, job_id=job_id, candidate_id=candidate_id
    )

    cached_score = Score(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_candidate_id=job_cand_id,
        fit_score=90,
        confidence=0.90,
        breakdown={},
        explanation="Cached match",
        skills_matched=["Python"],
        skills_missing=[],
        prompt_name="candidate_fit_scoring",
        prompt_version="2.0.0",
        model_version="gpt-4o-2024-08-06",
        is_current=True,
        created_at=datetime.datetime.now(datetime.UTC) - datetime.timedelta(hours=2),
    )
    score_repo.get_current_score.return_value = cached_score

    response = await service.score_candidate_sync(
        session=session,
        tenant_id=tenant_id,
        user_role="recruiter",
        job_id=job_id,
        candidate_id=candidate_id,
        force_rescore=False,
    )

    assert response.data.fit_score == 90
    score_repo.create_score.assert_not_called()


@pytest.mark.asyncio
async def test_score_unauthorized_role_raises_403() -> None:
    """Verify user with role 'member' raises InsufficientScorePermissionsError."""
    service = ScoreService()
    session = AsyncMock()

    with pytest.raises(InsufficientScorePermissionsError):
        await service.score_candidate_sync(
            session=session,
            tenant_id=uuid.uuid4(),
            user_role="member",
            job_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(),
        )
