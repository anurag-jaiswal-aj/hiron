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


def test_readiness_health_endpoint_before_db_initialization(client: TestClient) -> None:
    """Verify GET /api/v1/health/ready returns 503 Service Unavailable when subsystems are not initialized."""
    response = client.get("/api/v1/health/ready")
    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    data = response.json()
    assert data["status"] == "not_ready"
    assert "checks" in data
    assert data["checks"]["database"]["status"] == "not_initialized"
    assert data["checks"]["redis"]["status"] == "not_initialized"
