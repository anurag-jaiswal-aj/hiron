import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session
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

    async def mock_get_db():
        yield AsyncMock()

    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_db_session] = mock_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_get_task_status_success(client: TestClient) -> None:
    task_id = str(uuid.uuid4())

    mock_batch_job = MagicMock()
    mock_batch_job.status = "processing"
    mock_batch_job.queued_count = 10
    mock_batch_job.completed_count = 1
    mock_batch_job.failed_count = 1

    with patch("hiron.tasks.router.ScoreRepository.get_batch_score_job", new_callable=AsyncMock, return_value=mock_batch_job):
        resp = client.get(f"/api/v1/tasks/{task_id}")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["taskId"] == task_id
    assert data["status"] == "progress"
    assert data["progress"]["current"] == 2
    assert data["progress"]["total"] == 10
    assert data["progress"]["percent"] == 20.0

def test_get_task_status_not_uuid(client: TestClient) -> None:
    task_id = "not-a-uuid"

    resp = client.get(f"/api/v1/tasks/{task_id}")
    assert resp.status_code == 404
    assert "not found" in resp.json()["error"]["message"].lower()

def test_get_task_status_pending(client: TestClient) -> None:
    task_id = str(uuid.uuid4())

    mock_batch_job = MagicMock()
    mock_batch_job.status = "pending"

    with patch("hiron.tasks.router.ScoreRepository.get_batch_score_job", new_callable=AsyncMock, return_value=mock_batch_job):
        resp = client.get(f"/api/v1/tasks/{task_id}")

    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["status"] == "pending"
    assert data["progress"] is None
