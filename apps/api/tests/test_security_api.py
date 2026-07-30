"""API integration tests for GET /api/v1/security/audit REST endpoint."""

import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.main import create_app
from hiron.security.router import get_security_service
from hiron.security.schemas import (
    SecurityAuditReportData,
    SecurityAuditReportResponse,
    SecurityCheckResult,
)
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_sec_service() -> AsyncMock:
    """Fixture supplying mock SecurityService."""
    return AsyncMock()


@pytest.fixture
def client(mock_sec_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and SecurityService dependencies."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="admin@example.com",
        role="org_admin",
        is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_security_service] = lambda: mock_sec_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_get_security_audit_endpoint_success(
    client: TestClient, mock_sec_service: AsyncMock
) -> None:
    """Verify GET /api/v1/security/audit returns 200 OK per Phase 16."""
    mock_sec_service.run_security_audit.return_value = SecurityAuditReportResponse(
        data=SecurityAuditReportData(
            checks=[
                SecurityCheckResult(
                    name="SQL Injection Prevention",
                    category="Injection",
                    status="PASSED",
                    details="SQLAlchemy ORM parameterized queries.",
                )
            ],
            overall_score=100,
            compliance_status="COMPLIANT",
        )
    )

    response = client.get("/api/v1/security/audit")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["overallScore"] == 100
    assert res_data["complianceStatus"] == "COMPLIANT"
    assert len(res_data["checks"]) == 1
