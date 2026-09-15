import json
import typing
import uuid
from unittest.mock import MagicMock, patch

import pydantic
import pytest
from httpx import (
    ASGITransport,
    AsyncClient,
    HTTPStatusError,
    Request as HTTPXRequest,
    Response as HTTPXResponse,
)
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.candidates.models import Candidate
from hiron.common.exceptions import ResourceNotFoundException
from hiron.core.config import get_settings
from hiron.core.database import AsyncSessionLocal
from hiron.jobs.models import Job
from hiron.main import app
from hiron.scores.repository import ScoreRepository
from hiron.security.context import set_tenant_context
from hiron.tenants.models import Tenant
from tests.test_qstash_auth import CURRENT_KEY, NEXT_KEY, generate_qstash_signature


async def _seed_test_db(session: AsyncSession) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    tenant = Tenant(id=tenant_id, name="Webhook Tenant", slug=str(tenant_id))
    session.add(tenant)
    await session.flush()
    await session.execute(text(f"SET app.current_tenant_id = '{tenant_id}'"))

    job = Job(id=job_id, tenant_id=tenant_id, title="Webhook Job", description="Desc")
    session.add(job)
    candidate = Candidate(id=candidate_id, tenant_id=tenant_id, full_name="Webhook Cand")
    session.add(candidate)

    repo = ScoreRepository()
    batch_job = await repo.create_batch_score_job(session, tenant_id, job_id, 3)
    await session.commit()

    return tenant_id, job_id, candidate_id, batch_job.id


@pytest.fixture
async def async_client() -> typing.AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("QSTASH_CURRENT_SIGNING_KEY", CURRENT_KEY)
    monkeypatch.setenv("QSTASH_NEXT_SIGNING_KEY", NEXT_KEY)
    monkeypatch.setenv("QSTASH_WEBHOOK_URL", "http://testserver")
    monkeypatch.setenv("QSTASH_TOKEN", "fake_token")
    get_settings.cache_clear()


def create_mock_httpx_error(status_code: int) -> HTTPStatusError:
    request = HTTPXRequest("POST", "http://testserver")
    response = HTTPXResponse(status_code=status_code, request=request)
    return HTTPStatusError(f"Error {status_code}", request=request, response=response)


@pytest.mark.asyncio
async def test_batch_score_worker_webhook_success(async_client: AsyncClient) -> None:
    async with AsyncSessionLocal() as session:
        tenant_id, job_id, candidate_id, batch_id = await _seed_test_db(session)

    payload = {
        "batch_id": str(batch_id),
        "tenant_id": str(tenant_id),
        "job_id": str(job_id),
        "candidate_id": str(candidate_id),
        "force_rescore": False,
    }

    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/scores/batch/worker"
    )

    with patch("hiron.webhooks.router.ScoreService.score_candidate_sync") as mock_score:
        # Mock successful scoring
        mock_score.return_value = MagicMock()

        response = await async_client.post(
            "/api/v1/webhooks/qstash/scores/batch/worker",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "success",
            "batch_id": str(batch_id),
            "candidate_id": str(candidate_id),
        }

    # VERIFY DB MUTATION (Production Boundary)
    set_tenant_context(str(tenant_id))
    async with AsyncSessionLocal() as session:
        repo = ScoreRepository()
        persisted = await repo.get_batch_score_job(session, tenant_id, str(batch_id))
        assert persisted is not None
        assert persisted.completed_count == 1
        assert candidate_id in persisted.completed_candidate_ids


@pytest.mark.asyncio
async def test_batch_score_worker_webhook_resource_not_found(async_client: AsyncClient) -> None:
    async with AsyncSessionLocal() as session:
        tenant_id, job_id, candidate_id, batch_id = await _seed_test_db(session)

    payload = {
        "batch_id": str(batch_id),
        "tenant_id": str(tenant_id),
        "job_id": str(job_id),
        "candidate_id": str(candidate_id),
        "force_rescore": False,
    }

    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/scores/batch/worker"
    )

    with patch("hiron.webhooks.router.ScoreService.score_candidate_sync") as mock_score:
        mock_score.side_effect = ResourceNotFoundException("Entity missing")

        response = await async_client.post(
            "/api/v1/webhooks/qstash/scores/batch/worker",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "ignored"

    # VERIFY DB MUTATION (Production Boundary)
    set_tenant_context(str(tenant_id))
    async with AsyncSessionLocal() as session:
        repo = ScoreRepository()
        persisted = await repo.get_batch_score_job(session, tenant_id, str(batch_id))
        assert persisted is not None
        assert persisted.failed_count == 1
        assert candidate_id in persisted.failed_candidate_ids


@pytest.mark.asyncio
async def test_batch_score_worker_webhook_rate_limit(async_client: AsyncClient) -> None:
    payload = {
        "batch_id": "12345678-1234-5678-1234-567812345678",
        "tenant_id": str(uuid.uuid4()),
        "job_id": str(uuid.uuid4()),
        "candidate_id": str(uuid.uuid4()),
        "force_rescore": False,
    }

    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/scores/batch/worker"
    )

    with patch("hiron.webhooks.router.ScoreService.score_candidate_sync") as mock_score:
        mock_score.side_effect = create_mock_httpx_error(429)

        response = await async_client.post(
            "/api/v1/webhooks/qstash/scores/batch/worker",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 429


@pytest.mark.asyncio
async def test_batch_score_worker_webhook_ai_internal_error(async_client: AsyncClient) -> None:
    payload = {
        "batch_id": "12345678-1234-5678-1234-567812345678",
        "tenant_id": str(uuid.uuid4()),
        "job_id": str(uuid.uuid4()),
        "candidate_id": str(uuid.uuid4()),
        "force_rescore": False,
    }

    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/scores/batch/worker"
    )

    with patch("hiron.webhooks.router.ScoreService.score_candidate_sync") as mock_score:
        mock_score.side_effect = create_mock_httpx_error(503)

        response = await async_client.post(
            "/api/v1/webhooks/qstash/scores/batch/worker",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 503


@pytest.mark.asyncio
async def test_batch_score_worker_webhook_ai_schema_error(async_client: AsyncClient) -> None:
    payload = {
        "batch_id": "12345678-1234-5678-1234-567812345678",
        "tenant_id": str(uuid.uuid4()),
        "job_id": str(uuid.uuid4()),
        "candidate_id": str(uuid.uuid4()),
        "force_rescore": False,
    }

    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/scores/batch/worker"
    )

    with patch("hiron.webhooks.router.ScoreService.score_candidate_sync") as mock_score:
        # Pydantic validation error simulating bad schema from AI
        class DummyModel(pydantic.BaseModel):
            fit_score: int

        try:
            DummyModel.model_validate_json('{"fit_score": "not_an_int"}')
        except pydantic.ValidationError as ve:
            mock_score.side_effect = ve

        response = await async_client.post(
            "/api/v1/webhooks/qstash/scores/batch/worker",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        # Should return 200 OK so QStash drops the invalid message immediately
        assert response.status_code == 200
        assert response.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_batch_score_worker_webhook_malformed_payload(async_client: AsyncClient) -> None:
    payload = {
        "batch_id": "12345678-1234-5678-1234-567812345678",
        # Missing tenant_id etc.
    }

    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/scores/batch/worker"
    )

    response = await async_client.post(
        "/api/v1/webhooks/qstash/scores/batch/worker",
        content=body,
        headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
    )

    # Should return 200 OK so QStash drops the message instead of retrying endlessly
    assert response.status_code == 200
    assert response.json()["status"] == "failed"


@pytest.mark.asyncio
async def test_batch_score_worker_webhook_invalid_signature(async_client: AsyncClient) -> None:
    payload = {
        "batch_id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "job_id": str(uuid.uuid4()),
        "candidate_id": str(uuid.uuid4()),
        "force_rescore": False,
    }
    body = json.dumps(payload)

    # Send without signature or with invalid signature
    response = await async_client.post(
        "/api/v1/webhooks/qstash/scores/batch/worker",
        content=body,
        headers={
            "Upstash-Signature": "t=123,v1=invalid_signature",
            "Content-Type": "application/json",
        },
    )

    # Must reject with 401
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_batch_score_worker_webhook_cross_tenant_isolation(async_client: AsyncClient) -> None:
    from hiron.scores.repository import ScoreRepository
    from hiron.security.context import set_tenant_context

    # Create Tenant A and its data
    async with AsyncSessionLocal() as session:
        tenant_a, _job_a, _candidate_a, _batch_a = await _seed_test_db(session)
        # Create Tenant B and its data
        _tenant_b, job_b, candidate_b, batch_b = await _seed_test_db(session)

    # Tenant A tries to run worker for Tenant B's candidate
    # The payload is structurally valid and signed by QStash, claiming to act for Tenant A
    payload = {
        "batch_id": str(batch_b),
        "tenant_id": str(tenant_a),  # Authenticating as Tenant A
        "job_id": str(job_b),  # Target Tenant B's Job
        "candidate_id": str(candidate_b),  # Target Tenant B's Candidate
        "force_rescore": False,
    }

    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/scores/batch/worker"
    )

    response = await async_client.post(
        "/api/v1/webhooks/qstash/scores/batch/worker",
        content=body,
        headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
    )

    # Because RLS hides Tenant B's candidate from Tenant A, the webhook's DB lookup will fail.
    # The service layer returns ResourceNotFoundException, which the worker catches and acks (200 OK) with 'ignored'.
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert response.json()["reason"] == "Entity not found"


@pytest.mark.asyncio
async def test_batch_score_worker_webhook_clears_tenant_context(async_client: AsyncClient) -> None:
    from hiron.security.context import get_tenant_context

    payload = {
        "batch_id": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "job_id": str(uuid.uuid4()),
        "candidate_id": str(uuid.uuid4()),
        "force_rescore": False,
    }

    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/scores/batch/worker"
    )

    # Initial context should be None
    assert get_tenant_context() is None

    # We patch a failure to ensure the exception path (finally block) is exercised
    with patch("hiron.webhooks.router.ScoreService.score_candidate_sync") as mock_score:
        mock_score.side_effect = Exception("Boom")

        response = await async_client.post(
            "/api/v1/webhooks/qstash/scores/batch/worker",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 500

    # Ensure context was cleared
    assert get_tenant_context() is None
