"""API integration tests for NOTE-1 through NOTE-4 endpoints."""

import datetime
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.main import create_app
from hiron.notes.router import get_note_service
from hiron.notes.schemas import (
    NoteAuthorInfo,
    NoteData,
    NoteListResponse,
    NoteResponse,
)
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_note_service() -> AsyncMock:
    """Fixture supplying mock NoteService."""
    return AsyncMock()


@pytest.fixture
def client(mock_note_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and NoteService dependencies."""
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
    app.dependency_overrides[get_note_service] = lambda: mock_note_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_list_candidate_notes_endpoint_success(
    client: TestClient, mock_note_service: AsyncMock
) -> None:
    """Verify GET /api/v1/candidates/{id}/notes returns 200 OK per §NOTE-1."""
    candidate_id = uuid.uuid4()
    note_id = uuid.uuid4()

    mock_note_service.list_candidate_notes.return_value = NoteListResponse(
        data=[
            NoteData(
                id=note_id,
                candidate_id=candidate_id,
                author=NoteAuthorInfo(id=uuid.uuid4(), full_name="Jane Smith"),
                job_id=None,
                content="Great technical background",
                is_private=False,
                created_at=datetime.datetime.now(datetime.UTC),
                updated_at=datetime.datetime.now(datetime.UTC),
            )
        ]
    )

    response = client.get(f"/api/v1/candidates/{candidate_id}/notes")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert len(res_data) == 1
    assert res_data[0]["content"] == "Great technical background"


def test_create_note_endpoint_success(client: TestClient, mock_note_service: AsyncMock) -> None:
    """Verify POST /api/v1/candidates/{id}/notes returns 201 Created per §NOTE-2."""
    candidate_id = uuid.uuid4()
    note_id = uuid.uuid4()

    mock_note_service.create_note.return_value = NoteResponse(
        data=NoteData(
            id=note_id,
            candidate_id=candidate_id,
            author=NoteAuthorInfo(id=uuid.uuid4(), full_name="Jane Smith"),
            job_id=None,
            content="Follow up on system design skills",
            is_private=False,
            created_at=datetime.datetime.now(datetime.UTC),
            updated_at=datetime.datetime.now(datetime.UTC),
        )
    )

    response = client.post(
        f"/api/v1/candidates/{candidate_id}/notes",
        json={"content": "Follow up on system design skills", "isPrivate": False},
    )

    assert response.status_code == 201
    res_data = response.json()["data"]
    assert res_data["content"] == "Follow up on system design skills"


def test_archive_note_endpoint_success(client: TestClient, mock_note_service: AsyncMock) -> None:
    """Verify DELETE /api/v1/candidates/{id}/notes/{note_id} returns 204 No Content per §NOTE-4."""
    candidate_id = uuid.uuid4()
    note_id = uuid.uuid4()

    response = client.delete(f"/api/v1/candidates/{candidate_id}/notes/{note_id}")

    assert response.status_code == 204
    mock_note_service.archive_note.assert_called_once()
