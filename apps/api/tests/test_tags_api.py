"""API integration tests for TAG-1 through TAG-3 endpoints."""

import datetime
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.main import create_app
from hiron.tags.router import get_tag_service
from hiron.tags.schemas import (
    TagData,
    TagListResponse,
    TagResponse,
    TagUserPayload,
)
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_tag_service() -> AsyncMock:
    """Fixture supplying mock TagService."""
    return AsyncMock()


@pytest.fixture
def client(mock_tag_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and TagService dependencies."""
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
    app.dependency_overrides[get_tag_service] = lambda: mock_tag_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_list_candidate_tags_endpoint_success(
    client: TestClient, mock_tag_service: AsyncMock
) -> None:
    """Verify GET /api/v1/candidates/{id}/tags returns 200 OK per §TAG-1."""
    candidate_id = uuid.uuid4()
    tag_id = uuid.uuid4()

    mock_tag_service.list_candidate_tags.return_value = TagListResponse(
        data=[
            TagData(
                id=tag_id,
                tag_name="strong-hire",
                tagged_by=TagUserPayload(id=uuid.uuid4(), full_name="Jane Smith"),
                created_at=datetime.datetime.now(datetime.UTC),
            )
        ]
    )

    response = client.get(f"/api/v1/candidates/{candidate_id}/tags")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert len(res_data) == 1
    assert res_data[0]["tagName"] == "strong-hire"


def test_add_tag_endpoint_success(client: TestClient, mock_tag_service: AsyncMock) -> None:
    """Verify POST /api/v1/candidates/{id}/tags returns 201 Created per §TAG-2."""
    candidate_id = uuid.uuid4()
    tag_id = uuid.uuid4()

    mock_tag_service.add_tag.return_value = TagResponse(
        data=TagData(
            id=tag_id,
            tag_name="culture-fit",
            tagged_by=TagUserPayload(id=uuid.uuid4(), full_name="Jane Smith"),
            created_at=datetime.datetime.now(datetime.UTC),
        )
    )

    response = client.post(
        f"/api/v1/candidates/{candidate_id}/tags",
        json={"tagName": "Culture-Fit"},
    )

    assert response.status_code == 201
    res_data = response.json()["data"]
    assert res_data["tagName"] == "culture-fit"


def test_remove_tag_endpoint_success(client: TestClient, mock_tag_service: AsyncMock) -> None:
    """Verify DELETE /api/v1/candidates/{id}/tags/{tag_id} returns 204 No Content per §TAG-3."""
    candidate_id = uuid.uuid4()
    tag_id = uuid.uuid4()

    response = client.delete(f"/api/v1/candidates/{candidate_id}/tags/{tag_id}")

    assert response.status_code == 204
    mock_tag_service.remove_tag.assert_called_once()
