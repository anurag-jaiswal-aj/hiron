"""API integration tests for candidate, job embedding endpoints and status dashboard per API Contract §EMBED-1..3."""

import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.embeddings.router import get_embedding_service
from hiron.embeddings.schemas import (
    CandidateEmbeddingResponseData,
    CoverageMetricData,
    EmbeddingStatusData,
    EmbeddingStatusResponse,
    GenerateCandidateEmbeddingResponse,
    GenerateJobEmbeddingResponse,
    IndividualEmbeddingStatusData,
    IndividualEmbeddingStatusResponse,
    JobEmbeddingResponseData,
)
from hiron.main import create_app
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_embedding_service() -> AsyncMock:
    """Fixture supplying mock EmbeddingService."""
    return AsyncMock()


@pytest.fixture
def client(mock_embedding_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and EmbeddingService dependencies."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="recruiter@example.com",
        role="recruiter",
        is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
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
                model_version="gemini-embedding-2",
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
            model_version="gemini-embedding-2",
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
                model_version="gemini-embedding-2",
            ),
            jobs=CoverageMetricData(
                total=5,
                with_embedding=5,
                stale=0,
                missing=0,
                model_version="gemini-embedding-2",
            ),
        )
    )

    response = client.get("/api/v1/embeddings/status")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["candidates"]["total"] == 10
    assert res_data["candidates"]["withEmbedding"] == 8
    assert res_data["jobs"]["withEmbedding"] == 5


def test_get_candidate_embedding_status_endpoint_success(
    client: TestClient, mock_embedding_service: AsyncMock
) -> None:
    """Verify GET /api/v1/embeddings/candidates/{id} returns status."""
    candidate_id = uuid.uuid4()
    mock_embedding_service.get_candidate_embedding_status.return_value = (
        IndividualEmbeddingStatusResponse(
            data=IndividualEmbeddingStatusData(status="current", model_version="model1")
        )
    )
    res = client.get(f"/api/v1/embeddings/candidates/{candidate_id}")
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "current"


def test_get_job_embedding_status_endpoint_success(
    client: TestClient, mock_embedding_service: AsyncMock
) -> None:
    """Verify GET /api/v1/embeddings/jobs/{id} returns status."""
    job_id = uuid.uuid4()
    mock_embedding_service.get_job_embedding_status.return_value = (
        IndividualEmbeddingStatusResponse(
            data=IndividualEmbeddingStatusData(status="missing", model_version="model1")
        )
    )
    res = client.get(f"/api/v1/embeddings/jobs/{job_id}")
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "missing"


def test_get_candidate_embedding_status_unauthorized_other_tenant(
    client: TestClient, mock_embedding_service: AsyncMock
) -> None:
    """Verify candidate from another tenant cannot be inspected."""
    from hiron.common.exceptions import ResourceNotFoundException

    mock_embedding_service.get_candidate_embedding_status.side_effect = ResourceNotFoundException(
        "Not found"
    )
    res = client.get(f"/api/v1/embeddings/candidates/{uuid.uuid4()}")
    assert res.status_code == 404


def test_get_job_embedding_status_unauthorized_other_tenant(
    client: TestClient, mock_embedding_service: AsyncMock
) -> None:
    """Verify job from another tenant cannot be inspected."""
    from hiron.common.exceptions import ResourceNotFoundException

    mock_embedding_service.get_job_embedding_status.side_effect = ResourceNotFoundException(
        "Not found"
    )
    res = client.get(f"/api/v1/embeddings/jobs/{uuid.uuid4()}")
    assert res.status_code == 404
