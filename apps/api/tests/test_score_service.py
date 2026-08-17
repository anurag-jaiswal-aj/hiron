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


@pytest.fixture(autouse=True)
def force_qstash_engine(monkeypatch):
    monkeypatch.setenv("QSTASH_WEBHOOK_URL", "http://localhost:8000")
    from hiron.core.config import get_settings
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_score_candidate_sync_success() -> None:
    """Verify score_candidate_sync runs scoring engine and saves new score."""
    score_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()
    emb_repo = AsyncMock()

    mock_engine = AsyncMock()
    mock_engine.evaluate.return_value = {
        "fit_score": 85,
        "confidence": 0.85,
        "breakdown": {},
        "explanation": "Good match",
        "skills_matched": ["Python"],
        "skills_missing": [],
        "warnings": [],
        "prompt_name": "candidate_fit_scoring",
        "prompt_version": "2.0.0",
        "model_version": "models/gemini-2.5-flash",
        "input_tokens": 1250,
        "output_tokens": 350,
        "latency_ms": 420,
    }

    ai_usage_service = AsyncMock()

    service = ScoreService(
        score_repository=score_repo,
        candidate_repository=cand_repo,
        job_repository=job_repo,
        embedding_repository=emb_repo,
        scoring_engine=mock_engine,
        ai_usage_service=ai_usage_service,
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
    ai_usage_service.record_ai_usage.assert_called_once_with(
        session=session,
        tenant_id=tenant_id,
        operation="generate_candidate_score",
        model_version="models/gemini-2.5-flash",
        prompt_name="candidate_fit_scoring",
        prompt_version="2.0.0",
        input_tokens=1250,
        output_tokens=350,
        latency_ms=420,
        cost_usd=1250 / 1_000_000 * 0.075 + 350 / 1_000_000 * 0.30,
        status="success",
        is_cache_hit=False,
    )


@pytest.mark.asyncio
async def test_score_candidate_sync_idempotent_cached_response() -> None:
    """Verify score_candidate_sync returns cached score within 24h when force_rescore=False."""
    score_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()

    ai_usage_service = AsyncMock()

    service = ScoreService(
        score_repository=score_repo,
        candidate_repository=cand_repo,
        job_repository=job_repo,
        ai_usage_service=ai_usage_service,
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
    ai_usage_service.record_ai_usage.assert_called_once_with(
        session=session,
        tenant_id=tenant_id,
        operation="generate_candidate_score",
        model_version="gpt-4o-2024-08-06",
        prompt_name="candidate_fit_scoring",
        prompt_version="2.0.0",
        input_tokens=0,
        output_tokens=0,
        latency_ms=0,
        cost_usd=0.0,
        status="success",
        is_cache_hit=True,
    )


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


@pytest.mark.asyncio
async def test_score_candidate_sync_gemini_failure() -> None:
    """Verify Gemini failure prevents score creation and telemetry recording."""
    score_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()
    emb_repo = AsyncMock()
    mock_engine = AsyncMock()
    ai_usage_service = AsyncMock()

    mock_engine.evaluate.side_effect = Exception("Gemini HTTP Error")

    service = ScoreService(
        score_repository=score_repo,
        candidate_repository=cand_repo,
        job_repository=job_repo,
        embedding_repository=emb_repo,
        scoring_engine=mock_engine,
        ai_usage_service=ai_usage_service,
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    cand_repo.get_candidate_by_id.return_value = Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="Jane Doe"
    )
    job_repo.get_job_by_id.return_value = Job(id=job_id, tenant_id=tenant_id, title="Backend Dev")
    cand_repo.get_job_candidate.return_value = JobCandidate(
        id=uuid.uuid4(), tenant_id=tenant_id, job_id=job_id, candidate_id=candidate_id
    )
    score_repo.get_current_score.return_value = None

    with pytest.raises(Exception, match="Gemini HTTP Error"):
        await service.score_candidate_sync(
            session=session,
            tenant_id=tenant_id,
            user_role="recruiter",
            job_id=job_id,
            candidate_id=candidate_id,
        )

    score_repo.create_score.assert_not_called()
    ai_usage_service.record_ai_usage.assert_not_called()


@pytest.mark.asyncio
async def test_score_candidate_sync_persistence_failure() -> None:
    """Verify score persistence failure prevents telemetry recording."""
    score_repo = AsyncMock()
    cand_repo = AsyncMock()
    job_repo = AsyncMock()
    emb_repo = AsyncMock()
    mock_engine = AsyncMock()
    ai_usage_service = AsyncMock()

    mock_engine.evaluate.return_value = {
        "fit_score": 85,
        "confidence": 0.85,
        "breakdown": {},
        "explanation": "Good match",
        "skills_matched": ["Python"],
        "skills_missing": [],
        "warnings": [],
        "prompt_name": "candidate_fit_scoring",
        "prompt_version": "2.0.0",
        "model_version": "models/gemini-2.5-flash",
        "input_tokens": 1250,
        "output_tokens": 350,
        "latency_ms": 420,
    }

    score_repo.create_score.side_effect = Exception("Database Error")

    service = ScoreService(
        score_repository=score_repo,
        candidate_repository=cand_repo,
        job_repository=job_repo,
        embedding_repository=emb_repo,
        scoring_engine=mock_engine,
        ai_usage_service=ai_usage_service,
    )
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    cand_repo.get_candidate_by_id.return_value = Candidate(
        id=candidate_id, tenant_id=tenant_id, full_name="Jane Doe"
    )
    job_repo.get_job_by_id.return_value = Job(id=job_id, tenant_id=tenant_id, title="Backend Dev")
    cand_repo.get_job_candidate.return_value = JobCandidate(
        id=uuid.uuid4(), tenant_id=tenant_id, job_id=job_id, candidate_id=candidate_id
    )
    score_repo.get_current_score.return_value = None

    with pytest.raises(Exception, match="Database Error"):
        await service.score_candidate_sync(
            session=session,
            tenant_id=tenant_id,
            user_role="recruiter",
            job_id=job_id,
            candidate_id=candidate_id,
        )

    score_repo.create_score.assert_called_once()
    ai_usage_service.record_ai_usage.assert_not_called()


from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.core.database import AsyncSessionLocal
from hiron.scores.repository import ScoreRepository
from hiron.security.context import set_tenant_context
from hiron.tenants.models import Tenant


async def _create_test_tenant_and_job_and_candidate(
    session: AsyncSession,
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    tenant = Tenant(id=tenant_id, name="Test Tenant", slug=str(tenant_id))
    session.add(tenant)
    await session.flush()

    # We must explicitly set current_tenant_id for RLS policies!
    await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))

    job = Job(id=job_id, tenant_id=tenant_id, title="Test Job", description="Test Description")
    session.add(job)

    candidate = Candidate(id=candidate_id, tenant_id=tenant_id, full_name="Test Cand")
    session.add(candidate)

    await session.commit()
    return tenant_id, job_id, candidate_id


@pytest.mark.asyncio
async def test_regression_batch_score_job_persistence() -> None:
    """TEST 2: Verify BatchScoreJob persistence is committed before coordinator depends on it."""
    async with AsyncSessionLocal() as session:
        tenant_id, job_id, _ = await _create_test_tenant_and_job_and_candidate(session)

    set_tenant_context(str(tenant_id))

    # Run the method using a real session and real repo
    service = ScoreService()
    async with AsyncSessionLocal() as session:
        # We manually commit here because we want to test the repository boundary
        # Actually, create_batch_score_job is called by ScoreService.batch_score_async
        # But we just want to ensure it persists.
        repo = ScoreRepository()
        batch_job = await repo.create_batch_score_job(
            session=session, tenant_id=tenant_id, job_id=job_id, queued_count=3
        )
        await session.commit()
        batch_id = str(batch_job.id)

    # Open NEW session to verify persistence (simulating the QStash worker reading it)
    async with AsyncSessionLocal() as session2:
        repo = ScoreRepository()
        persisted = await repo.get_batch_score_job(session2, tenant_id, batch_id)
        assert persisted is not None
        assert persisted.status == "pending"
        assert persisted.queued_count == 3


@pytest.mark.asyncio
async def test_regression_worker_success_accounting() -> None:
    """TEST 3: Verify worker success accounting persists completed_count."""
    async with AsyncSessionLocal() as session:
        tenant_id, job_id, candidate_id = await _create_test_tenant_and_job_and_candidate(session)
    set_tenant_context(str(tenant_id))
    async with AsyncSessionLocal() as session:
        repo = ScoreRepository()
        batch_job = await repo.create_batch_score_job(session, tenant_id, job_id, 3)
        await session.commit()
        batch_id = str(batch_job.id)

    # Simulate worker success webhook explicit commit
    async with AsyncSessionLocal() as session2:
        repo = ScoreRepository()
        claimed = await repo.claim_batch_score_worker_success(
            session2, tenant_id, batch_id, candidate_id
        )
        assert claimed is True
        await session2.commit()

    # Verify persistence
    async with AsyncSessionLocal() as session3:
        repo = ScoreRepository()
        persisted = await repo.get_batch_score_job(session3, tenant_id, batch_id)
        assert persisted.completed_count == 1
        assert candidate_id in persisted.completed_candidate_ids


@pytest.mark.asyncio
async def test_regression_worker_failure_accounting() -> None:
    """TEST 4: Verify worker failure accounting persists failed_count."""
    async with AsyncSessionLocal() as session:
        tenant_id, job_id, candidate_id = await _create_test_tenant_and_job_and_candidate(session)
    set_tenant_context(str(tenant_id))
    async with AsyncSessionLocal() as session:
        repo = ScoreRepository()
        batch_job = await repo.create_batch_score_job(session, tenant_id, job_id, 3)
        await session.commit()
        batch_id = str(batch_job.id)

    # Simulate worker failure webhook explicit commit
    async with AsyncSessionLocal() as session2:
        repo = ScoreRepository()
        claimed = await repo.claim_batch_score_worker_failure(
            session2, tenant_id, batch_id, candidate_id
        )
        assert claimed is True
        await session2.commit()

    # Verify persistence
    async with AsyncSessionLocal() as session3:
        repo = ScoreRepository()
        persisted = await repo.get_batch_score_job(session3, tenant_id, batch_id)
        assert persisted.failed_count == 1
        assert candidate_id in persisted.failed_candidate_ids


@pytest.mark.asyncio
async def test_regression_duplicate_worker_idempotency() -> None:
    """TEST 5: Verify duplicate worker delivery remains idempotent after commit."""
    async with AsyncSessionLocal() as session:
        tenant_id, job_id, candidate_id = await _create_test_tenant_and_job_and_candidate(session)
    set_tenant_context(str(tenant_id))
    async with AsyncSessionLocal() as session:
        repo = ScoreRepository()
        batch_job = await repo.create_batch_score_job(session, tenant_id, job_id, 3)
        await session.commit()
        batch_id = str(batch_job.id)

    # First delivery
    async with AsyncSessionLocal() as session2:
        repo = ScoreRepository()
        claimed1 = await repo.claim_batch_score_worker_success(
            session2, tenant_id, batch_id, candidate_id
        )
        assert claimed1 is True
        await session2.commit()

    # Second duplicate delivery (QStash retry or dupe)
    async with AsyncSessionLocal() as session3:
        repo = ScoreRepository()
        claimed2 = await repo.claim_batch_score_worker_success(
            session3, tenant_id, batch_id, candidate_id
        )
        # Should return False because it was already claimed and committed
        assert claimed2 is False
        await session3.commit()

    # Verify persistence didn't double-increment
    async with AsyncSessionLocal() as session4:
        repo = ScoreRepository()
        persisted = await repo.get_batch_score_job(session4, tenant_id, batch_id)
        assert persisted.completed_count == 1
        assert len(persisted.completed_candidate_ids) == 1
