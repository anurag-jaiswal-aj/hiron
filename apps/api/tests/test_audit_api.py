"""API integration tests for AUDIT-1 and AUDIT-2 REST endpoints."""

import datetime
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.audit.router import get_audit_service
from hiron.audit.schemas import (
    AuditActorInfo,
    AuditLogData,
    AuditLogListResponse,
    AuditPagination,
)
from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.main import create_app
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_audit_service() -> AsyncMock:
    """Fixture supplying mock AuditService."""
    return AsyncMock()


@pytest.fixture
def client(mock_audit_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and AuditService dependencies."""
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
    app.dependency_overrides[get_db] = lambda: AsyncMock()
    app.dependency_overrides[get_audit_service] = lambda: mock_audit_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_list_audit_logs_endpoint_success(
    client: TestClient, mock_audit_service: AsyncMock
) -> None:
    """Verify GET /api/v1/audit-logs returns 200 OK per §AUDIT-1."""
    entity_id = uuid.uuid4()
    log_id = uuid.uuid4()

    mock_audit_service.list_audit_logs.return_value = AuditLogListResponse(
        data=[
            AuditLogData(
                id=log_id,
                action="stage_changed",
                entity_type="job_candidate",
                entity_id=entity_id,
                actor=AuditActorInfo(id=uuid.uuid4(), full_name="Jane Admin"),
                changes={"before": {"stage": "Screening"}, "after": {"stage": "Interview"}},
                ip_address="127.0.0.1",
                created_at=datetime.datetime.now(datetime.UTC),
            )
        ],
        pagination=AuditPagination(has_more=False, next_cursor=None, total_count=1),
    )

    response = client.get("/api/v1/audit-logs")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert len(res_data) == 1
    assert res_data[0]["action"] == "stage_changed"
    assert res_data[0]["entityType"] == "job_candidate"


def test_get_entity_audit_logs_endpoint_success(
    client: TestClient, mock_audit_service: AsyncMock
) -> None:
    """Verify GET /api/v1/audit-logs/entity/{entity_type}/{entity_id} returns 200 OK per §AUDIT-2."""
    entity_id = uuid.uuid4()

    mock_audit_service.get_entity_audit_logs.return_value = AuditLogListResponse(
        data=[
            AuditLogData(
                id=uuid.uuid4(),
                action="created",
                entity_type="candidate",
                entity_id=entity_id,
                actor=AuditActorInfo(id=uuid.uuid4(), full_name="Jane Admin"),
                changes=None,
                ip_address="127.0.0.1",
                created_at=datetime.datetime.now(datetime.UTC),
            )
        ],
        pagination=AuditPagination(has_more=False, next_cursor=None, total_count=1),
    )

    response = client.get(f"/api/v1/audit-logs/entity/candidate/{entity_id}")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert len(res_data) == 1
    assert res_data[0]["action"] == "created"
