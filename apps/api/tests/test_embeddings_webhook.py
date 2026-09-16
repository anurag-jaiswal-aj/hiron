import uuid
import json
from collections.abc import AsyncGenerator
from unittest.mock import patch, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy import select, text
from sqlalchemy.exc import OperationalError

from hiron.common.exceptions import ResourceNotFoundException
from hiron.core.config import get_settings
from hiron.embeddings.service import PipelineResult, EmbeddingService
from hiron.embeddings.models import CandidateEmbedding, JobEmbedding
from hiron.main import app
from tests.test_qstash_auth import CURRENT_KEY, NEXT_KEY, generate_qstash_signature


ADMIN_DB_URL = "postgresql+asyncpg://hiron_user:hiron_secure_password@localhost:5432/hiron_dev"


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
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


@pytest.fixture
async def db_engine() -> AsyncGenerator[AsyncEngine, None]:
    engine = create_async_engine(ADMIN_DB_URL, echo=False)
    yield engine
    await engine.dispose()


@pytest.fixture
async def real_db(db_engine: AsyncEngine) -> AsyncGenerator[AsyncSession, None]:
    async_session_maker = async_sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
        await session.rollback()


# ================================
# RESTORED ORIGINAL TESTS (TASK 2)
# ================================


@pytest.mark.asyncio
async def test_candidate_embedding_webhook_valid_signature_success(
    async_client: AsyncClient,
) -> None:
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    payload = {
        "tenant_id": tenant_id,
        "candidate_id": candidate_id,
        "model_version": "test-model-1",
    }
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
async def test_candidate_embedding_webhook_missing_signature_rejected(
    async_client: AsyncClient,
) -> None:
    tenant_id = str(uuid.uuid4())
    candidate_id = str(uuid.uuid4())
    payload = {
        "tenant_id": tenant_id,
        "candidate_id": candidate_id,
        "model_version": "test-model-1",
    }
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
async def test_job_embedding_webhook_valid_signature_success(async_client: AsyncClient) -> None:
    tenant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    payload = {"tenant_id": tenant_id, "job_id": job_id, "model_version": "test-model-1"}
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
async def test_job_embedding_webhook_rate_limit_returns_429(async_client: AsyncClient) -> None:
    tenant_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    payload = {"tenant_id": tenant_id, "job_id": job_id, "model_version": "test-model-1"}
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


# ================================
# REAL DB INTEGRATION TESTS (TASK 3 & 4)
# ================================


@pytest.mark.asyncio
async def test_candidate_terminal_failure_integration(
    async_client: AsyncClient, real_db: AsyncSession
) -> None:
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    await real_db.execute(
        text(
            "INSERT INTO tenants (id, name, slug) VALUES (:tid, 'Test Tenant', :slug) ON CONFLICT DO NOTHING"
        ),
        {"tid": tenant_id, "slug": f"test-tenant-{tenant_id}"},
    )
    await real_db.execute(
        text(
            "INSERT INTO candidates (id, tenant_id, full_name, email, phone, location, current_title, current_company, summary, is_archived) VALUES (:cid, :tid, 'Test Cand', 'a@b.c', '123', 'NY', 'Eng', 'Acme', 'desc', false) ON CONFLICT DO NOTHING"
        ),
        {"cid": candidate_id, "tid": tenant_id},
    )
    await real_db.commit()

    payload = {
        "tenant_id": str(tenant_id),
        "candidate_id": str(candidate_id),
        "model_version": "test-model",
    }
    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/embeddings/candidate"
    )

    class ClientError(Exception):
        code: int

    terminal_error = ClientError("400 error")
    terminal_error.code = 400

    with patch(
        "hiron.embeddings.generator.EmbeddingGenerator.generate_embedding",
        side_effect=terminal_error,
    ):
        response = await async_client.post(
            "/api/v1/webhooks/qstash/embeddings/candidate",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    res = await real_db.execute(
        select(CandidateEmbedding).where(CandidateEmbedding.candidate_id == candidate_id)
    )
    db_emb = res.scalar_one_or_none()
    assert db_emb is not None
    assert db_emb.status == "failed"
    assert db_emb.error_type == "client_error_400"
    assert db_emb.embedding is None

    await real_db.execute(
        text("DELETE FROM candidate_embeddings WHERE candidate_id = :cid"), {"cid": candidate_id}
    )
    await real_db.execute(text("DELETE FROM candidates WHERE id = :cid"), {"cid": candidate_id})
    await real_db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tenant_id})
    await real_db.commit()


@pytest.mark.asyncio
async def test_job_terminal_failure_integration(
    async_client: AsyncClient, real_db: AsyncSession
) -> None:
    tenant_id = uuid.uuid4()
    job_id = uuid.uuid4()

    await real_db.execute(
        text(
            "INSERT INTO tenants (id, name, slug) VALUES (:tid, 'Test Tenant', :slug) ON CONFLICT DO NOTHING"
        ),
        {"tid": tenant_id, "slug": f"test-tenant-{tenant_id}"},
    )
    await real_db.execute(
        text(
            "INSERT INTO jobs (id, tenant_id, title, location, status, description) VALUES (:jid, :tid, 'Test Job', 'NY', 'draft', 'desc') ON CONFLICT DO NOTHING"
        ),
        {"jid": job_id, "tid": tenant_id},
    )
    await real_db.commit()

    payload = {"tenant_id": str(tenant_id), "job_id": str(job_id), "model_version": "test-model"}
    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/embeddings/job"
    )

    class ClientError(Exception):
        code: int

    terminal_error = ClientError("400 error")
    terminal_error.code = 400

    with patch(
        "hiron.embeddings.generator.EmbeddingGenerator.generate_embedding",
        side_effect=terminal_error,
    ):
        response = await async_client.post(
            "/api/v1/webhooks/qstash/embeddings/job",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.json()["status"] == "failed"

    res = await real_db.execute(select(JobEmbedding).where(JobEmbedding.job_id == job_id))
    db_emb = res.scalar_one_or_none()
    assert db_emb is not None
    assert db_emb.status == "failed"
    assert db_emb.error_type == "client_error_400"
    assert db_emb.embedding is None

    await real_db.execute(text("DELETE FROM job_embeddings WHERE job_id = :jid"), {"jid": job_id})
    await real_db.execute(text("DELETE FROM jobs WHERE id = :jid"), {"jid": job_id})
    await real_db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tenant_id})
    await real_db.commit()


@pytest.mark.asyncio
async def test_candidate_transient_failure_integration(
    async_client: AsyncClient, real_db: AsyncSession
) -> None:
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    await real_db.execute(
        text(
            "INSERT INTO tenants (id, name, slug) VALUES (:tid, 'Test Tenant', :slug) ON CONFLICT DO NOTHING"
        ),
        {"tid": tenant_id, "slug": f"test-tenant-{tenant_id}"},
    )
    await real_db.execute(
        text(
            "INSERT INTO candidates (id, tenant_id, full_name, email, phone, location, current_title, current_company, summary, is_archived) VALUES (:cid, :tid, 'Test Cand', 'a@b.c', '123', 'NY', 'Eng', 'Acme', 'desc', false) ON CONFLICT DO NOTHING"
        ),
        {"cid": candidate_id, "tid": tenant_id},
    )
    await real_db.commit()

    payload = {
        "tenant_id": str(tenant_id),
        "candidate_id": str(candidate_id),
        "model_version": "test-model",
    }
    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/embeddings/candidate"
    )

    with patch(
        "hiron.embeddings.generator.EmbeddingGenerator.generate_embedding",
        side_effect=ValueError("Unexpected genai format"),
    ):
        response = await async_client.post(
            "/api/v1/webhooks/qstash/embeddings/candidate",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )
        assert response.status_code == 500

    res = await real_db.execute(
        select(CandidateEmbedding).where(CandidateEmbedding.candidate_id == candidate_id)
    )
    assert res.scalar_one_or_none() is None

    await real_db.execute(text("DELETE FROM candidates WHERE id = :cid"), {"cid": candidate_id})
    await real_db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tenant_id})
    await real_db.commit()


@pytest.mark.asyncio
async def test_failure_state_db_commit_failure(
    async_client: AsyncClient, real_db: AsyncSession
) -> None:
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    await real_db.execute(
        text(
            "INSERT INTO tenants (id, name, slug) VALUES (:tid, 'Test Tenant', :slug) ON CONFLICT DO NOTHING"
        ),
        {"tid": tenant_id, "slug": f"test-tenant-{tenant_id}"},
    )
    await real_db.execute(
        text(
            "INSERT INTO candidates (id, tenant_id, full_name, email, phone, location, current_title, current_company, summary, is_archived) VALUES (:cid, :tid, 'Test Cand', 'a@b.c', '123', 'NY', 'Eng', 'Acme', 'desc', false) ON CONFLICT DO NOTHING"
        ),
        {"cid": candidate_id, "tid": tenant_id},
    )
    await real_db.commit()

    payload = {
        "tenant_id": str(tenant_id),
        "candidate_id": str(candidate_id),
        "model_version": "test-model",
    }
    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/embeddings/candidate"
    )

    class ClientError(Exception):
        code: int

    terminal_error = ClientError("400 error")
    terminal_error.code = 400

    with (
        patch(
            "hiron.embeddings.generator.EmbeddingGenerator.generate_embedding",
            side_effect=terminal_error,
        ),
        patch(
            "sqlalchemy.ext.asyncio.AsyncSession.commit",
            side_effect=OperationalError("db down", None, Exception()),
        ),
    ):
        response = await async_client.post(
            "/api/v1/webhooks/qstash/embeddings/candidate",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )
        assert response.status_code == 500

    await real_db.execute(text("DELETE FROM candidates WHERE id = :cid"), {"cid": candidate_id})
    await real_db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tenant_id})
    await real_db.commit()


@pytest.mark.asyncio
async def test_successful_cache_hit_behavior(
    async_client: AsyncClient, real_db: AsyncSession
) -> None:
    tenant_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    await real_db.execute(
        text(
            "INSERT INTO tenants (id, name, slug) VALUES (:tid, 'Test Tenant', :slug) ON CONFLICT DO NOTHING"
        ),
        {"tid": tenant_id, "slug": f"test-tenant-{tenant_id}"},
    )
    await real_db.execute(
        text(
            "INSERT INTO candidates (id, tenant_id, full_name, email, phone, location, current_title, current_company, summary, is_archived) VALUES (:cid, :tid, 'Test Cand', 'a@b.c', '123', 'NY', 'Eng', 'Acme', 'desc', false) ON CONFLICT DO NOTHING"
        ),
        {"cid": candidate_id, "tid": tenant_id},
    )

    source_text_hash = "dummyhash"
    dummy_vector_str = "[" + ",".join(["0.0"] * 768) + "]"
    await real_db.execute(
        text(
            "INSERT INTO candidate_embeddings (tenant_id, candidate_id, model_version, source_text_hash, embedding, status) VALUES (:tid, :cid, 'test-model', :hsh, CAST(:emb AS vector), 'success')"
        ),
        {"tid": tenant_id, "cid": candidate_id, "hsh": source_text_hash, "emb": dummy_vector_str},
    )
    await real_db.commit()

    payload = {
        "tenant_id": str(tenant_id),
        "candidate_id": str(candidate_id),
        "model_version": "test-model",
    }
    body = json.dumps(payload)
    signature = generate_qstash_signature(
        body, CURRENT_KEY, url="http://testserver/api/v1/webhooks/qstash/embeddings/candidate"
    )

    with (
        patch(
            "hiron.embeddings.generator.EmbeddingGenerator.compute_source_text_hash",
            return_value=source_text_hash,
        ),
        patch("hiron.embeddings.generator.EmbeddingGenerator.generate_embedding") as mock_gen,
    ):
        response = await async_client.post(
            "/api/v1/webhooks/qstash/embeddings/candidate",
            content=body,
            headers={"Upstash-Signature": signature, "Content-Type": "application/json"},
        )

        assert response.status_code == 200
        assert response.json() == {"status": "success", "cache_hit": True}
        mock_gen.assert_not_called()

    await real_db.execute(
        text("DELETE FROM candidate_embeddings WHERE candidate_id = :cid"), {"cid": candidate_id}
    )
    await real_db.execute(text("DELETE FROM candidates WHERE id = :cid"), {"cid": candidate_id})
    await real_db.execute(text("DELETE FROM tenants WHERE id = :tid"), {"tid": tenant_id})
    await real_db.commit()


@pytest.mark.asyncio
async def test_failed_status_reporting() -> None:
    service = EmbeddingService()
    mock_session = MagicMock()
    mock_candidate = MagicMock()
    mock_existing = MagicMock()
    mock_existing.status = "failed"
    mock_existing.source_text_hash = "dummy_hash"
    mock_existing.model_version = "test-model-1"

    with (
        patch.object(service.candidate_repo, "get_candidate_by_id", return_value=mock_candidate),
        patch.object(
            service.embedding_repo, "get_latest_candidate_embedding", return_value=mock_existing
        ),
        patch.object(service, "_construct_candidate_source_text", return_value="dummy_text"),
        patch.object(service.generator, "compute_source_text_hash", return_value="dummy_hash"),
    ):
        res = await service.get_candidate_embedding_status(
            mock_session, uuid.uuid4(), uuid.uuid4(), "test-model-1"
        )
        assert res.data.status == "failed"
