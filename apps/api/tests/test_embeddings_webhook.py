import uuid
from unittest.mock import patch

import pytest
from httpx import ASGITransport, AsyncClient

from hiron.core.config import get_settings
from hiron.embeddings.service import PipelineResult
from hiron.main import app
from tests.test_qstash_auth import CURRENT_KEY, NEXT_KEY, generate_qstash_signature


@pytest.fixture
async def async_client():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    monkeypatch.setenv("QSTASH_CURRENT_SIGNING_KEY", CURRENT_KEY)
    monkeypatch.setenv("QSTASH_NEXT_SIGNING_KEY", NEXT_KEY)
    monkeypatch.setenv("QSTASH_WEBHOOK_URL", "http://testserver")
    monkeypatch.setenv("QSTASH_TOKEN", "fake_token")
    get_settings.cache_clear()


@pytest.mark.asyncio
async def test_candidate_embedding_webhook_valid_signature_success(async_client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    payload = {
        "tenant_id": tenant_id,
        "candidate_id": candidate_id,
        "model_version": "test-model-1",
    }

    # We must construct exactly the JSON string that will be sent
    import json

    body = json.dumps(payload)

    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/embeddings/candidate"
    )

    with patch(
        "hiron.webhooks.router.EmbeddingService.generate_candidate_embedding_pipeline"
    ) as mock_pipeline:
        mock_pipeline.return_value = PipelineResult(
            cache_hit=False,
            model_version="test-model-1",
            input_tokens=100,
            total_tokens=100,
            latency_ms=50,
            status="success",
            error_type=None,
        )

        response = await async_client.post(
            "/api/v1/webhooks/qstash/embeddings/candidate",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "success", "cache_hit": False}
        mock_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_candidate_embedding_webhook_missing_signature_rejected(async_client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    payload = {
        "tenant_id": tenant_id,
        "candidate_id": candidate_id,
        "model_version": "test-model-1",
    }

    import json

    body = json.dumps(payload)

    with patch(
        "hiron.webhooks.router.EmbeddingService.generate_candidate_embedding_pipeline"
    ) as mock_pipeline:
        response = await async_client.post(
            "/api/v1/webhooks/qstash/embeddings/candidate",
            content=body,
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 401
        mock_pipeline.assert_not_called()


@pytest.mark.asyncio
async def test_job_embedding_webhook_valid_signature_success(async_client):
    tenant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    payload = {"tenant_id": tenant_id, "job_id": job_id, "model_version": "test-model-1"}

    import json

    body = json.dumps(payload)

    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/embeddings/job"
    )

    with patch(
        "hiron.webhooks.router.EmbeddingService.generate_job_embedding_pipeline"
    ) as mock_pipeline:
        mock_pipeline.return_value = PipelineResult(
            cache_hit=False,
            model_version="test-model-1",
            input_tokens=100,
            total_tokens=100,
            latency_ms=50,
            status="success",
            error_type=None,
        )

        response = await async_client.post(
            "/api/v1/webhooks/qstash/embeddings/job",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "success", "cache_hit": False}
        mock_pipeline.assert_called_once()


@pytest.mark.asyncio
async def test_job_embedding_webhook_rate_limit_returns_429(async_client):
    tenant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    payload = {"tenant_id": tenant_id, "job_id": job_id, "model_version": "test-model-1"}

    import json

    body = json.dumps(payload)

    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/embeddings/job"
    )

    with patch(
        "hiron.webhooks.router.EmbeddingService.generate_job_embedding_pipeline"
    ) as mock_pipeline:
        mock_pipeline.return_value = PipelineResult(
            cache_hit=False,
            model_version="test-model-1",
            input_tokens=0,
            total_tokens=0,
            latency_ms=50,
            status="failed",
            error_type="rate_limit",
        )

        response = await async_client.post(
            "/api/v1/webhooks/qstash/embeddings/job",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 429
        mock_pipeline.assert_called_once()
