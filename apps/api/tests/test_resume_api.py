"""API integration tests for Resume Upload and polling endpoints per API Contract §RES-1..RES-4."""

import uuid
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session
from hiron.main import create_app
from hiron.resumes.router import get_resume_service
from hiron.resumes.schemas import (
    BulkUploadResumeResponse,
    ResumeStatusResponse,
    UploadResumeResponse,
)
from hiron.users.models import User


@pytest.fixture
def recruiter_user() -> User:
    """Fixture providing an active recruiter User."""
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="recruiter@company.com",
        full_name="Alex Recruiter",
        role="recruiter",
        is_active=True,
        is_email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def auth_headers(recruiter_user: User) -> dict[str, str]:
    """Fixture providing valid Authorization header."""
    _ = recruiter_user
    return {"Authorization": "Bearer fake-token"}


@pytest.fixture
def mock_db_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_resume_service() -> AsyncMock:
    """Fixture providing a mock ResumeService."""
    return AsyncMock()


@pytest.fixture
def client(
    recruiter_user: User,
    mock_db_session: AsyncMock,
    mock_resume_service: AsyncMock,
) -> TestClient:
    """Fixture providing FastAPI TestClient with overridden dependencies."""
    app = create_app()

    async def _override_get_current_user() -> User:
        return recruiter_user

    async def _override_get_db_session() -> AsyncGenerator[AsyncMock, None]:
        yield mock_db_session

    def _override_get_resume_service() -> AsyncMock:
        return mock_resume_service

    app.dependency_overrides[get_current_user] = _override_get_current_user
    app.dependency_overrides[get_db_session] = _override_get_db_session
    app.dependency_overrides[get_resume_service] = _override_get_resume_service

    return TestClient(app)


def test_upload_single_resume_endpoint_success(
    client: TestClient,
    auth_headers: dict[str, str],
    mock_resume_service: AsyncMock,
) -> None:
    """Verify POST /api/v1/resumes/upload returns 202 Accepted with UploadResumeResponse per §RES-1."""
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_resume_service.upload_resume.return_value = UploadResumeResponse(
        resume_id=resume_id,
        candidate_id=candidate_id,
        task_id="task-12345",
        status="pending",
        status_url=f"/api/v1/resumes/{resume_id}/status",
    )

    files = {"file": ("john_doe_resume.pdf", b"%PDF-1.4 sample content", "application/pdf")}
    response = client.post(
        "/api/v1/resumes/upload",
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    payload = response.json()
    assert payload["data"]["resumeId"] == str(resume_id)
    assert payload["data"]["candidateId"] == str(candidate_id)
    assert payload["data"]["status"] == "pending"


def test_bulk_upload_resumes_endpoint_success(
    client: TestClient,
    auth_headers: dict[str, str],
    mock_resume_service: AsyncMock,
) -> None:
    """Verify POST /api/v1/resumes/bulk-upload returns 202 Accepted per §RES-2."""
    mock_resume_service.bulk_upload_resumes.return_value = BulkUploadResumeResponse(
        task_id="task-bulk-123",
        total_files=2,
        accepted=2,
        rejected=0,
        rejections=[],
        status_url="/api/v1/tasks/task-bulk-123",
    )

    files = [
        ("files", ("resume1.pdf", b"%PDF-1.4 file 1", "application/pdf")),
        ("files", ("resume2.pdf", b"%PDF-1.4 file 2", "application/pdf")),
    ]
    response = client.post(
        "/api/v1/resumes/bulk-upload",
        files=files,
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    payload = response.json()
    assert payload["data"]["totalFiles"] == 2
    assert payload["data"]["accepted"] == 2


def test_get_resume_status_endpoint_success(
    client: TestClient,
    auth_headers: dict[str, str],
    mock_resume_service: AsyncMock,
) -> None:
    """Verify GET /api/v1/resumes/{resume_id}/status returns parsing status per §RES-3."""
    resume_id = uuid.uuid4()
    mock_resume_service.get_resume_status.return_value = ResumeStatusResponse(
        resume_id=resume_id,
        status="parsed",
        parse_confidence=0.92,
        parsed_data={"skills": ["Python", "FastAPI"]},
        parse_error=None,
        parser_model_version="en_core_web_trf-3.7.3",
        created_at=datetime.now(UTC),
    )

    response = client.get(
        f"/api/v1/resumes/{resume_id}/status",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    payload = response.json()
    assert payload["data"]["resumeId"] == str(resume_id)
    assert payload["data"]["status"] == "parsed"


def test_retry_resume_parse_endpoint_success(
    client: TestClient,
    auth_headers: dict[str, str],
    mock_resume_service: AsyncMock,
) -> None:
    """Verify POST /api/v1/resumes/{resume_id}/retry resets status to pending per §RES-4."""
    resume_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_resume_service.retry_parse.return_value = UploadResumeResponse(
        resume_id=resume_id,
        candidate_id=candidate_id,
        task_id="task-retry-999",
        status="pending",
        status_url=f"/api/v1/resumes/{resume_id}/status",
    )

    response = client.post(
        f"/api/v1/resumes/{resume_id}/retry",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    payload = response.json()
    assert payload["data"]["resumeId"] == str(resume_id)
    assert payload["data"]["status"] == "pending"
