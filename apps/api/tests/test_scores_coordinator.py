import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from hiron.core.config import get_settings
from hiron.main import app
from hiron.scores.models import BatchScoreJob
from tests.test_qstash_auth import CURRENT_KEY, generate_qstash_signature


def qstash_headers(body: str, url: str) -> dict:
    signature = generate_qstash_signature(body, CURRENT_KEY, url=url)
    return {"Upstash-Signature": signature}


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def mock_qstash_keys(monkeypatch):
    monkeypatch.setenv("QSTASH_CURRENT_SIGNING_KEY", CURRENT_KEY)
    monkeypatch.setenv("QSTASH_NEXT_SIGNING_KEY", CURRENT_KEY)
    monkeypatch.setenv("QSTASH_WEBHOOK_URL", "http://testserver")
    get_settings.cache_clear()


@pytest.fixture
def mock_qstash_publisher(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("hiron.core.qstash_client.qstash_publisher.publish", mock)
    return mock


@pytest.fixture
def mock_score_repo(monkeypatch):
    repo_mock = AsyncMock()
    monkeypatch.setattr("hiron.scores.service.ScoreRepository", lambda: repo_mock)

    # We also mock ScoreService internals to prevent real DB interaction
    mock_score_sync = AsyncMock()
    monkeypatch.setattr("hiron.scores.service.ScoreService.score_candidate_sync", mock_score_sync)
    return repo_mock


@pytest.mark.asyncio
async def test_coordinator_zero_candidates(async_client: AsyncClient, mock_score_repo):
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    batch_id = uuid.uuid4()

    mock_score_repo.get_batch_score_job.return_value = BatchScoreJob(
        id=batch_id,
        tenant_id=tenant_id,
        job_id=job_id,
        status="pending",
        queued_count=0,
        completed_count=0,
        failed_count=0,
    )

    payload = {
        "batch_id": str(batch_id),
        "tenant_id": str(tenant_id),
        "job_id": str(job_id),
        "candidate_ids": [],
        "force_rescore": False,
    }
    body = json.dumps(payload)
    url = "http://testserver/api/v1/webhooks/qstash/scores/batch/coordinator"

    response = await async_client.post(url, content=body, headers=qstash_headers(body, url))
    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    batch = mock_score_repo.get_batch_score_job.return_value
    assert batch.status == "completed"


@pytest.mark.asyncio
async def test_coordinator_fan_out_creates_workers(
    async_client: AsyncClient, mock_score_repo, mock_qstash_publisher
):
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_score_repo.get_batch_score_job.return_value = BatchScoreJob(
        id=batch_id,
        tenant_id=tenant_id,
        job_id=job_id,
        status="pending",
        queued_count=1,
    )
    mock_score_repo.transition_batch_score_job_to_processing.return_value = 1

    payload = {
        "batch_id": str(batch_id),
        "tenant_id": str(tenant_id),
        "job_id": str(job_id),
        "candidate_ids": [str(candidate_id)],
        "force_rescore": False,
    }
    body = json.dumps(payload)
    url = "http://testserver/api/v1/webhooks/qstash/scores/batch/coordinator"

    response = await async_client.post(url, content=body, headers=qstash_headers(body, url))
    assert response.status_code == 200
    assert response.json()["status"] == "processing"

    mock_qstash_publisher.assert_called_once()
    kwargs = mock_qstash_publisher.call_args.kwargs
    assert kwargs["payload"]["candidate_id"] == str(candidate_id)
    assert (
        kwargs["deduplication_id"] == f"batch-worker-{tenant_id}-{job_id}-{candidate_id}-{batch_id}"
    )


@pytest.mark.asyncio
async def test_coordinator_idempotency_terminal_state(
    async_client: AsyncClient, mock_score_repo, mock_qstash_publisher
):
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    batch_id = uuid.uuid4()

    mock_score_repo.get_batch_score_job.return_value = BatchScoreJob(
        id=batch_id,
        tenant_id=tenant_id,
        job_id=job_id,
        status="completed",
        queued_count=1,
    )

    payload = {
        "batch_id": str(batch_id),
        "tenant_id": str(tenant_id),
        "job_id": str(job_id),
        "candidate_ids": [str(uuid.uuid4())],
        "force_rescore": False,
    }
    body = json.dumps(payload)
    url = "http://testserver/api/v1/webhooks/qstash/scores/batch/coordinator"

    response = await async_client.post(url, content=body, headers=qstash_headers(body, url))
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"

    mock_qstash_publisher.assert_not_called()


@pytest.mark.asyncio
async def test_worker_success_atomic_accounting(
    async_client: AsyncClient, monkeypatch, mock_score_repo
):
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    payload = {
        "batch_id": str(batch_id),
        "tenant_id": str(tenant_id),
        "job_id": str(job_id),
        "candidate_id": str(candidate_id),
        "force_rescore": False,
    }
    body = json.dumps(payload)
    url = "http://testserver/api/v1/webhooks/qstash/scores/batch/worker"

    mock_score = AsyncMock()
    monkeypatch.setattr(
        "hiron.scores.service.ScoreService.score_candidate_sync", mock_score, raising=False
    )

    mock_score_repo.claim_batch_score_worker_success.return_value = True

    with patch(
        "hiron.webhooks.router.ScoreService",
        return_value=AsyncMock(score_repo=mock_score_repo, score_candidate_sync=mock_score),
    ):
        response = await async_client.post(url, content=body, headers=qstash_headers(body, url))

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    mock_score_repo.claim_batch_score_worker_success.assert_called_once()


@pytest.mark.asyncio
async def test_worker_failure_atomic_accounting(async_client: AsyncClient, mock_score_repo):
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    payload = {
        "batch_id": str(batch_id),
        "tenant_id": str(tenant_id),
        "job_id": str(job_id),
        "candidate_id": str(candidate_id),
        "force_rescore": False,
    }
    body = json.dumps(payload)
    url = "http://testserver/api/v1/webhooks/qstash/scores/batch/worker"

    import httpx

    mock_score = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Bad Request", request=httpx.Request("POST", ""), response=httpx.Response(400)
        )
    )

    mock_score_repo.claim_batch_score_worker_failure.return_value = True

    with patch(
        "hiron.webhooks.router.ScoreService",
        return_value=AsyncMock(score_repo=mock_score_repo, score_candidate_sync=mock_score),
    ):
        response = await async_client.post(url, content=body, headers=qstash_headers(body, url))

    assert response.status_code == 200
    assert response.json()["status"] == "failed"
    mock_score_repo.claim_batch_score_worker_failure.assert_called_once()


@pytest.mark.asyncio
async def test_worker_retryable_failure_does_not_alter_counters(
    async_client: AsyncClient, mock_score_repo
):
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    batch_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    payload = {
        "batch_id": str(batch_id),
        "tenant_id": str(tenant_id),
        "job_id": str(job_id),
        "candidate_id": str(candidate_id),
        "force_rescore": False,
    }
    body = json.dumps(payload)
    url = "http://testserver/api/v1/webhooks/qstash/scores/batch/worker"

    import httpx

    mock_score = AsyncMock(
        side_effect=httpx.HTTPStatusError(
            "Rate Limit", request=httpx.Request("POST", ""), response=httpx.Response(429)
        )
    )

    with patch(
        "hiron.webhooks.router.ScoreService",
        return_value=AsyncMock(score_repo=mock_score_repo, score_candidate_sync=mock_score),
    ):
        response = await async_client.post(url, content=body, headers=qstash_headers(body, url))

    assert response.status_code == 429
    mock_score_repo.claim_batch_score_worker_success.assert_not_called()
    mock_score_repo.claim_batch_score_worker_failure.assert_not_called()
