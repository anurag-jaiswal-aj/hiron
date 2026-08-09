"""Integration test suite for Candidate Management API endpoints per API Contract §CAND-1 through §CAND-6."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.candidates.models import Candidate, JobCandidate
from hiron.candidates.router import (
    get_candidate_service,
    jobs_candidate_router,
    router as candidates_router,
)
from hiron.candidates.service import CandidateService
from hiron.common.exceptions import register_exception_handlers
from hiron.core.database import get_db_session
from hiron.jobs.models import PipelineStage
from hiron.users.models import User


@pytest.fixture
def mock_db() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


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
def mock_candidate_service() -> AsyncMock:
    """Fixture providing a mock CandidateService."""
    return AsyncMock(spec=CandidateService)


@pytest.fixture
def client(
    mock_db: AsyncMock,
    mock_candidate_service: AsyncMock,
    recruiter_user: User,
) -> Generator[TestClient, None, None]:
    """TestClient configured with dependency overrides for Candidate API routes."""
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(candidates_router, prefix="/api/v1/candidates")
    test_app.include_router(jobs_candidate_router, prefix="/api/v1/jobs")

    test_app.dependency_overrides[get_db_session] = lambda: mock_db
    test_app.dependency_overrides[get_candidate_service] = lambda: mock_candidate_service
    test_app.dependency_overrides[get_current_user] = lambda: recruiter_user

    with TestClient(test_app) as test_client:
        yield test_client


def test_list_candidates_endpoint_success(
    client: TestClient,
    mock_candidate_service: AsyncMock,
    recruiter_user: User,
) -> None:
    """Verify GET /api/v1/candidates returns 200 OK and list of candidate records."""
    c1 = Candidate(
        id=uuid.uuid4(),
        tenant_id=recruiter_user.tenant_id,
        full_name="Sarah Connor",
        email="sarah@example.com",
        current_title="Lead Engineer",
        current_company="Cyberdyne",
        skills=["Python", "C++"],
        source="upload",
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_candidate_service.list_candidates.return_value = ([c1], 1, None)

    response = client.get("/api/v1/candidates")
    assert response.status_code == 200
    data = response.json()["data"]["data"]
    assert len(data) == 1
    assert data[0]["fullName"] == "Sarah Connor"
    assert data[0]["email"] == "sarah@example.com"


def test_list_candidates_with_tag_filtering(
    client: TestClient,
    mock_candidate_service: AsyncMock,
) -> None:
    """Verify GET /api/v1/candidates passes the tag parameter to the service."""
    mock_candidate_service.list_candidates.return_value = ([], 0, None)

    response = client.get("/api/v1/candidates?tag=senior")
    assert response.status_code == 200

    # Ensure the tag parameter was correctly passed down
    mock_candidate_service.list_candidates.assert_called_once()
    kwargs = mock_candidate_service.list_candidates.call_args.kwargs
    assert kwargs.get("tag") == "senior"


def test_create_candidate_endpoint_success(
    client: TestClient,
    mock_candidate_service: AsyncMock,
    recruiter_user: User,
) -> None:
    """Verify POST /api/v1/candidates creates candidate profile and returns 201 Created."""
    c_id = uuid.uuid4()
    candidate = Candidate(
        id=c_id,
        tenant_id=recruiter_user.tenant_id,
        full_name="John Connor",
        email="john@example.com",
        skills=["Leadership", "Strategy"],
        source="upload",
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_candidate_service.create_candidate.return_value = candidate

    response = client.post(
        "/api/v1/candidates",
        json={
            "fullName": "John Connor",
            "email": "john@example.com",
            "skills": ["Leadership", "Strategy"],
        },
    )

    assert response.status_code == 201
    res_data = response.json()["data"]
    assert res_data["id"] == str(c_id)
    assert res_data["fullName"] == "John Connor"


def test_get_candidate_endpoint_success(
    client: TestClient,
    mock_candidate_service: AsyncMock,
    recruiter_user: User,
) -> None:
    """Verify GET /api/v1/candidates/{candidate_id} returns 200 OK and profile details."""
    c_id = uuid.uuid4()
    candidate = Candidate(
        id=c_id,
        tenant_id=recruiter_user.tenant_id,
        full_name="Kyle Reese",
        email="kyle@example.com",
        skills=["Defense"],
        is_archived=False,
        job_associations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_candidate_service.get_candidate_by_id.return_value = candidate

    response = client.get(f"/api/v1/candidates/{c_id}")
    assert response.status_code == 200
    assert response.json()["data"]["fullName"] == "Kyle Reese"


def test_update_candidate_endpoint_success(
    client: TestClient,
    mock_candidate_service: AsyncMock,
    recruiter_user: User,
) -> None:
    """Verify PATCH /api/v1/candidates/{candidate_id} returns 200 OK and updated profile."""
    c_id = uuid.uuid4()
    candidate = Candidate(
        id=c_id,
        tenant_id=recruiter_user.tenant_id,
        full_name="Kyle Reese Updated",
        email="kyle@example.com",
        skills=["Defense", "Tactics"],
        is_archived=False,
        job_associations=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_candidate_service.update_candidate.return_value = candidate

    response = client.patch(
        f"/api/v1/candidates/{c_id}",
        json={"fullName": "Kyle Reese Updated"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["fullName"] == "Kyle Reese Updated"


def test_archive_candidate_endpoint_success(
    client: TestClient,
    mock_candidate_service: AsyncMock,
    recruiter_user: User,
) -> None:
    """Verify POST /api/v1/candidates/{candidate_id}/archive soft deletes candidate."""
    c_id = uuid.uuid4()
    candidate = Candidate(
        id=c_id,
        tenant_id=recruiter_user.tenant_id,
        full_name="Kyle Reese",
        email="kyle@example.com",
        is_archived=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_candidate_service.archive_candidate.return_value = candidate

    response = client.post(f"/api/v1/candidates/{c_id}/archive")
    assert response.status_code == 200
    assert response.json()["data"]["isArchived"] is True


def test_add_candidate_to_job_endpoint_success(
    client: TestClient,
    mock_candidate_service: AsyncMock,
    recruiter_user: User,
) -> None:
    """Verify POST /api/v1/jobs/{job_id}/candidates returns 201 Created and stage summary."""
    job_id = uuid.uuid4()
    c_id = uuid.uuid4()
    stage_id = uuid.uuid4()

    stage = PipelineStage(
        id=stage_id,
        tenant_id=recruiter_user.tenant_id,
        job_id=job_id,
        name="Applied",
        position=1,
    )
    jc = JobCandidate(
        id=uuid.uuid4(),
        tenant_id=recruiter_user.tenant_id,
        job_id=job_id,
        candidate_id=c_id,
        current_stage_id=stage_id,
        is_shortlisted=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    jc.current_stage = stage
    mock_candidate_service.add_candidate_to_job.return_value = jc

    response = client.post(
        f"/api/v1/jobs/{job_id}/candidates",
        json={"candidateId": str(c_id)},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["jobId"] == str(job_id)
    assert data["candidateId"] == str(c_id)
    assert data["currentStage"]["name"] == "Applied"
