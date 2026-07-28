"""Integration tests for Core API health check endpoints per API Contract §HEALTH-1 & §HEALTH-2."""

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from hiron.main import app


@pytest.fixture
def client() -> TestClient:
    """Return a TestClient instance for the FastAPI app."""
    return TestClient(app)


def test_liveness_health_endpoint(client: TestClient) -> None:
    """Verify GET /api/v1/health returns 200 OK with healthy status and version."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "timestamp" in data


def test_readiness_health_endpoint_structure(client: TestClient) -> None:
    """Verify GET /api/v1/health/ready returns valid readiness structure with database check."""
    response = client.get("/api/v1/health/ready")
    # Response code is either 200 (if DB is running locally) or 503 (if DB is unreachable)
    assert response.status_code in (status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE)
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "redis" in data["checks"]
    assert data["checks"]["redis"]["status"] == "not_initialized"
