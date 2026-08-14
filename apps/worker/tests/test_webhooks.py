import json
import time
import base64
import hashlib
import uuid
from unittest.mock import patch

import jwt
import pytest
from httpx import ASGITransport, AsyncClient

from hiron.core.config import get_settings
from apps.worker.src.main import app

CURRENT_KEY = "sig_current_test_key_123"
NEXT_KEY = "sig_next_test_key_456"


def generate_qstash_signature(
    body: str,
    key: str,
    url: str,
) -> str:
    now = int(time.time())
    body_hash = hashlib.sha256(body.encode()).digest()
    body_hash_b64 = base64.urlsafe_b64encode(body_hash).decode().rstrip("=")

    payload = {
        "iss": "Upstash",
        "sub": url,
        "exp": now + 3600,
        "nbf": now - 3600,
        "body": body_hash_b64,
    }
    return jwt.encode(payload, key, algorithm="HS256")


@pytest.fixture
async def async_client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client:
        yield client


@pytest.fixture(autouse=True)
def mock_settings(monkeypatch):
    monkeypatch.setenv("QSTASH_CURRENT_SIGNING_KEY", CURRENT_KEY)
    monkeypatch.setenv("QSTASH_NEXT_SIGNING_KEY", NEXT_KEY)
    get_settings.cache_clear()


@pytest.mark.asyncio
@patch("apps.worker.src.main.generate_candidate_embedding_worker_pipeline")
async def test_webhook_candidate_valid_signature_success(mock_pipeline, async_client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    
    body_dict = {
        "tenant_id": tenant_id,
        "candidate_id": candidate_id,
        "model_version": "gemini-embedding-2"
    }
    body_str = json.dumps(body_dict)
    
    url = "http://testserver/api/v1/webhooks/qstash/embeddings/candidate"
    signature = generate_qstash_signature(body_str, CURRENT_KEY, url=url)
    
    mock_pipeline.return_value = None
    
    response = await async_client.post(
        "/api/v1/webhooks/qstash/embeddings/candidate",
        content=body_str,
        headers={"Upstash-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    mock_pipeline.assert_called_once()
    kwargs = mock_pipeline.call_args.kwargs
    assert str(kwargs["tenant_id"]) == tenant_id
    assert str(kwargs["candidate_id"]) == candidate_id


@pytest.mark.asyncio
@patch("apps.worker.src.main.generate_job_embedding_worker_pipeline")
async def test_webhook_job_valid_signature_success(mock_pipeline, async_client):
    tenant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    
    body_dict = {
        "tenant_id": tenant_id,
        "job_id": job_id,
        "model_version": "gemini-embedding-2"
    }
    body_str = json.dumps(body_dict)
    
    url = "http://testserver/api/v1/webhooks/qstash/embeddings/job"
    signature = generate_qstash_signature(body_str, CURRENT_KEY, url=url)
    
    mock_pipeline.return_value = None
    
    response = await async_client.post(
        "/api/v1/webhooks/qstash/embeddings/job",
        content=body_str,
        headers={"Upstash-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 200
    assert response.json() == {"status": "success"}
    mock_pipeline.assert_called_once()
    kwargs = mock_pipeline.call_args.kwargs
    assert str(kwargs["tenant_id"]) == tenant_id
    assert str(kwargs["job_id"]) == job_id


@pytest.mark.asyncio
async def test_webhook_invalid_signature_rejected(async_client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    
    body_dict = {
        "tenant_id": tenant_id,
        "candidate_id": candidate_id,
        "model_version": "gemini-embedding-2"
    }
    body_str = json.dumps(body_dict)
    
    url = "http://testserver/api/v1/webhooks/qstash/embeddings/candidate"
    signature = generate_qstash_signature(body_str, "wrong_key", url=url)
    
    response = await async_client.post(
        "/api/v1/webhooks/qstash/embeddings/candidate",
        content=body_str,
        headers={"Upstash-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_webhook_malformed_payload_rejected(async_client):
    body_str = json.dumps({"tenant_id": "invalid-uuid"})
    url = "http://testserver/api/v1/webhooks/qstash/embeddings/candidate"
    signature = generate_qstash_signature(body_str, CURRENT_KEY, url=url)
    
    response = await async_client.post(
        "/api/v1/webhooks/qstash/embeddings/candidate",
        content=body_str,
        headers={"Upstash-Signature": signature, "Content-Type": "application/json"}
    )
    
    assert response.status_code == 422


@pytest.mark.asyncio
@patch("apps.worker.src.main.generate_candidate_embedding_worker_pipeline")
async def test_webhook_pipeline_exception_propagates(mock_pipeline, async_client):
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    
    body_dict = {
        "tenant_id": tenant_id,
        "candidate_id": candidate_id,
        "model_version": "gemini-embedding-2"
    }
    body_str = json.dumps(body_dict)
    
    url = "http://testserver/api/v1/webhooks/qstash/embeddings/candidate"
    signature = generate_qstash_signature(body_str, CURRENT_KEY, url=url)
    
    mock_pipeline.side_effect = Exception("Database connection failed")
    
    with pytest.raises(Exception, match="Database connection failed"):
        await async_client.post(
            "/api/v1/webhooks/qstash/embeddings/candidate",
            content=body_str,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"}
        )
