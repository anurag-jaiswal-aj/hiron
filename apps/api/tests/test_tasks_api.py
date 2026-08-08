import uuid
from collections.abc import Generator
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.main import create_app
from hiron.users.models import User

app = create_app()

@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    tenant_id = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
    user_id = uuid.uuid4()

    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="recruiter@example.com",
        role="recruiter",
        is_active=True,
    )

    app.dependency_overrides[get_current_user] = lambda: mock_user

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_get_task_status_success(client: TestClient) -> None:
    tenant_id = "550e8400-e29b-41d4-a716-446655440000"
    task_id = f"batch-{tenant_id}-12345"

    mock_result = MagicMock()
    mock_result.state = "PROGRESS"
    mock_result.info = {"current": 2, "total": 10, "percent": 20.0}

    with patch("hiron.tasks.router.celery_app.AsyncResult", return_value=mock_result):
        resp = client.get(f"/api/v1/tasks/{task_id}")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["taskId"] == task_id
    assert data["status"] == "progress"
    assert data["progress"]["current"] == 2
    assert data["progress"]["total"] == 10
    assert data["progress"]["percent"] == 20.0

def test_get_task_status_wrong_tenant(client: TestClient) -> None:
    wrong_tenant_id = "11111111-1111-1111-1111-111111111111"
    task_id = f"batch-{wrong_tenant_id}-12345"

    resp = client.get(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]["message"].lower()

def test_get_task_status_pending(client: TestClient) -> None:
    tenant_id = "550e8400-e29b-41d4-a716-446655440000"
    task_id = f"batch-{tenant_id}-12345"

    mock_result = MagicMock()
    mock_result.state = "PENDING"
    mock_result.info = None

    with patch("hiron.tasks.router.celery_app.AsyncResult", return_value=mock_result):
        resp = client.get(f"/api/v1/tasks/{task_id}")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "pending"
    assert data["progress"] is None
