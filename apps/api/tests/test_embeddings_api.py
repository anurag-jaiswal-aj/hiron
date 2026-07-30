"""API integration tests for candidate, job embedding endpoints and status dashboard per API Contract §EMBED-1..3."""

import uuid
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.auth.schemas import UserContext
from hiron.database import get_db
from hiron.embeddings.router import get_embedding_service
from hiron.embeddings.schemas import (
    CandidateEmbeddingResponseData,
    CoverageMetricData,
    EmbeddingStatusData,
    EmbeddingStatusResponse,
    GenerateCandidateEmbeddingResponse,
    GenerateJobEmbeddingResponse,
    JobEmbeddingResponseData,
)
from hiron.main import create_app

app = create_app()


@pytest.fixture
def mock_embedding_service() -> AsyncMock:
    """Fixture supplying mock EmbeddingService."""
    return AsyncMock()


@pytest.fixture
def client(mock_embedding_service: AsyncMock) -> TestClient:
    """TestClient fixture overriding user context and EmbeddingService dependencies."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    app.dependency_overrides[get_current_user] = lambda: UserContext(
        id=user_id,
        tenant_id=tenant_id,
        email="recruiter@example.com",
        role="recruiter",
        is_active=True,
    )
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    app.dependency_overrides[get_embedding_service] = lambda: mock_embedding_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_generate_candidate_embedding_endpoint_success(
    client: TestClient, mock_embedding_service: AsyncMock
) -> None:
    """Verify POST /api/v1/candidates/{id}/embedding returns 202 Accepted per §EMBED-1."""
    candidate_id = uuid.uuid4()
    mock_embedding_service.generate_candidate_embedding.return_value = (
        GenerateCandidateEmbeddingResponse(
            data=CandidateEmbeddingResponseData(
                candidate_id=candidate_id,
                task_id="task-123",
                status="processing",
                model_version="text-embedding-3-small",
            )
        )
    )

    response = client.post(f"/api/v1/candidates/{candidate_id}/embedding")

    assert response.status_code == 202
    res_data = response.json()["data"]
    assert res_data["candidateId"] == str(candidate_id)
    assert res_data["status"] == "processing"


def test_generate_job_embedding_endpoint_success(
    client: TestClient, mock_embedding_service: AsyncMock
) -> None:
    """Verify POST /api/v1/jobs/{id}/embedding returns 202 Accepted per §EMBED-2."""
    job_id = uuid.uuid4()
    mock_embedding_service.generate_job_embedding.return_value = GenerateJobEmbeddingResponse(
        data=JobEmbeddingResponseData(
            job_id=job_id,
            task_id="task-456",
            status="processing",
            model_version="text-embedding-3-small",
        )
    )

    response = client.post(f"/api/v1/jobs/{job_id}/embedding")

    assert response.status_code == 202
    res_data = response.json()["data"]
    assert res_data["jobId"] == str(job_id)
    assert res_data["status"] == "processing"


def test_get_embedding_status_endpoint_success(
    client: TestClient, mock_embedding_service: AsyncMock
) -> None:
    """Verify GET /api/v1/embeddings/status returns 200 OK coverage metrics per §EMBED-3."""
    mock_embedding_service.get_embedding_status.return_value = EmbeddingStatusResponse(
        data=EmbeddingStatusData(
            candidates=CoverageMetricData(
                total=10,
                with_embedding=8,
                stale=1,
                missing=1,
                model_version="text-embedding-3-small",
            ),
            jobs=CoverageMetricData(
                total=5,
                with_embedding=5,
                stale=0,
                missing=0,
                model_version="text-embedding-3-small",
            ),
        )
    )

    response = client.get("/api/v1/embeddings/status")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["candidates"]["total"] == 10
    assert res_data["candidates"]["withEmbedding"] == 8
    assert res_data["jobs"]["withEmbedding"] == 5
