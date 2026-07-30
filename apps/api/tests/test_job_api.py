"""Integration test suite for Jobs API endpoints, verifying authentication, RBAC permissions, and status transitions."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.common.exceptions import register_exception_handlers
from hiron.core.database import get_db_session
from hiron.jobs.exceptions import InsufficientJobPermissionsError, JobNotFoundError
from hiron.jobs.models import Job, PipelineStage
from hiron.jobs.router import get_job_service, router as jobs_router
from hiron.users.models import User


@pytest.fixture
def mock_db() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_job_service() -> AsyncMock:
    """Fixture providing a mock JobService."""
    service = AsyncMock()
    service.job_repo = AsyncMock()
    return service


@pytest.fixture
def mock_recruiter_user() -> User:
    """Fixture providing a recruiter User entity."""
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="recruiter@acme.com",
        full_name="Recruiter User",
        role="recruiter",
        is_active=True,
        is_email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_hm_user() -> User:
    """Fixture providing a hiring_manager User entity."""
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="hm@acme.com",
        full_name="Hiring Manager",
        role="hiring_manager",
        is_active=True,
        is_email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def client(
    mock_db: AsyncMock,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with dependency overrides for recruiter user."""
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(jobs_router, prefix="/api/v1/jobs")

    test_app.dependency_overrides[get_db_session] = lambda: mock_db
    test_app.dependency_overrides[get_job_service] = lambda: mock_job_service
    test_app.dependency_overrides[get_current_user] = lambda: mock_recruiter_user

    with TestClient(test_app) as test_client:
        yield test_client


def test_list_jobs_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify GET /api/v1/jobs returns 200 OK and job items list."""
    job_id = uuid.uuid4()
    job1 = Job(
        id=job_id,
        tenant_id=mock_recruiter_user.tenant_id,
        title="Senior Backend Engineer",
        description="Desc",
        department="Engineering",
        location="Remote",
        status="open",
        is_archived=False,
        employment_type="full_time",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_job_service.list_jobs.return_value = ([job1], 1)

    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    data = response.json()["data"]["data"]
    assert len(data) == 1
    assert data[0]["id"] == str(job_id)
    assert data[0]["title"] == "Senior Backend Engineer"


def test_get_job_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify GET /api/v1/jobs/{job_id} returns 200 OK and job details with stages."""
    job_id = uuid.uuid4()
    stage1 = PipelineStage(
        id=uuid.uuid4(),
        tenant_id=mock_recruiter_user.tenant_id,
        job_id=job_id,
        name="Applied",
        position=1,
        is_terminal=False,
        stage_type="active",
    )
    job = Job(
        id=job_id,
        tenant_id=mock_recruiter_user.tenant_id,
        title="Backend Lead",
        description="Full description",
        department="Engineering",
        status="draft",
        is_archived=False,
        pipeline_stages=[stage1],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_job_service.get_job_by_id.return_value = job

    response = client.get(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(job_id)
    assert data["title"] == "Backend Lead"
    assert len(data["pipelineStages"]) == 1
    assert data["pipelineStages"][0]["name"] == "Applied"


def test_get_job_endpoint_not_found(
    client: TestClient,
    mock_job_service: AsyncMock,
) -> None:
    """Verify GET /api/v1/jobs/{job_id} returns 404 when job does not exist."""
    mock_job_service.get_job_by_id.side_effect = JobNotFoundError()
    response = client.get(f"/api/v1/jobs/{uuid.uuid4()}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "RESOURCE_NOT_FOUND"


def test_create_job_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify POST /api/v1/jobs returns 201 Created and created job."""
    new_id = uuid.uuid4()
    created = Job(
        id=new_id,
        tenant_id=mock_recruiter_user.tenant_id,
        title="DevOps Specialist",
        description="Kubernetes infra",
        department="Infra",
        status="draft",
        is_archived=False,
        pipeline_stages=[],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_job_service.create_job.return_value = created
    mock_job_service.get_job_by_id.return_value = created

    response = client.post(
        "/api/v1/jobs",
        json={
            "title": "DevOps Specialist",
            "description": "Kubernetes infra",
            "department": "Infra",
            "employmentType": "full_time",
        },
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id"] == str(new_id)
    assert data["title"] == "DevOps Specialist"


def test_create_job_endpoint_validation_error(client: TestClient) -> None:
    """Verify POST /api/v1/jobs returns 422 Unprocessable Content on missing title."""
    response = client.post(
        "/api/v1/jobs",
        json={"description": "Missing title field"},
    )
    assert response.status_code == 422


def test_update_job_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify PATCH /api/v1/jobs/{job_id} returns 200 OK and updated payload."""
    job_id = uuid.uuid4()
    updated = Job(
        id=job_id,
        tenant_id=mock_recruiter_user.tenant_id,
        title="Updated Title",
        description="Updated Desc",
        status="draft",
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_job_service.update_job.return_value = updated

    response = client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Updated Title"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["title"] == "Updated Title"


def test_open_job_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify POST /api/v1/jobs/{job_id}/open returns 200 OK."""
    job_id = uuid.uuid4()
    opened = Job(
        id=job_id,
        tenant_id=mock_recruiter_user.tenant_id,
        title="Title",
        description="Desc",
        status="open",
        is_archived=False,
        opened_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_job_service.open_job.return_value = opened

    response = client.post(f"/api/v1/jobs/{job_id}/open")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "open"


def test_pause_job_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify POST /api/v1/jobs/{job_id}/pause returns 200 OK."""
    job_id = uuid.uuid4()
    paused = Job(
        id=job_id,
        tenant_id=mock_recruiter_user.tenant_id,
        title="Title",
        description="Desc",
        status="paused",
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_job_service.pause_job.return_value = paused

    response = client.post(f"/api/v1/jobs/{job_id}/pause")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "paused"


def test_close_job_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify POST /api/v1/jobs/{job_id}/close returns 200 OK."""
    job_id = uuid.uuid4()
    closed = Job(
        id=job_id,
        tenant_id=mock_recruiter_user.tenant_id,
        title="Title",
        description="Desc",
        status="closed",
        is_archived=False,
        closed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_job_service.close_job.return_value = closed

    response = client.post(
        f"/api/v1/jobs/{job_id}/close",
        json={"reason": "Position filled"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "closed"


def test_archive_job_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify POST /api/v1/jobs/{job_id}/archive returns 200 OK."""
    job_id = uuid.uuid4()
    archived = Job(
        id=job_id,
        tenant_id=mock_recruiter_user.tenant_id,
        title="Title",
        description="Desc",
        status="archived",
        is_archived=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_job_service.archive_job.return_value = archived

    response = client.post(f"/api/v1/jobs/{job_id}/archive")
    assert response.status_code == 200
    assert response.json()["data"]["isArchived"] is True


def test_delete_job_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
) -> None:
    """Verify DELETE /api/v1/jobs/{job_id} returns 204 No Content."""
    job_id = uuid.uuid4()
    mock_job_service.job_repo.delete_job.return_value = True

    response = client.delete(f"/api/v1/jobs/{job_id}")
    assert response.status_code == 204


def test_job_api_rbac_forbidden_for_hiring_manager(
    mock_db: AsyncMock,
    mock_job_service: AsyncMock,
    mock_hm_user: User,
) -> None:
    """Verify hiring manager receiving 403 Forbidden on job creation."""
    mock_job_service.create_job.side_effect = InsufficientJobPermissionsError()

    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(jobs_router, prefix="/api/v1/jobs")

    test_app.dependency_overrides[get_db_session] = lambda: mock_db
    test_app.dependency_overrides[get_job_service] = lambda: mock_job_service
    test_app.dependency_overrides[get_current_user] = lambda: mock_hm_user

    with TestClient(test_app) as hm_client:
        response = hm_client.post(
            "/api/v1/jobs",
            json={"title": "Title", "description": "Desc"},
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"


def test_list_job_pipeline_stages_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify GET /api/v1/jobs/{job_id}/stages returns list of stages."""
    job_id = uuid.uuid4()
    stage = PipelineStage(
        id=uuid.uuid4(),
        tenant_id=mock_recruiter_user.tenant_id,
        job_id=job_id,
        name="Tech Screen",
        position=1,
        is_terminal=False,
        stage_type="active",
    )
    mock_job_service.list_pipeline_stages.return_value = [stage]

    response = client.get(f"/api/v1/jobs/{job_id}/stages")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["name"] == "Tech Screen"


def test_create_job_pipeline_stage_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify POST /api/v1/jobs/{job_id}/stages returns 201 Created and new stage payload."""
    job_id = uuid.uuid4()
    new_stage = PipelineStage(
        id=uuid.uuid4(),
        tenant_id=mock_recruiter_user.tenant_id,
        job_id=job_id,
        name="System Architecture",
        position=3,
        is_terminal=False,
        stage_type="active",
    )
    mock_job_service.create_pipeline_stage.return_value = new_stage

    response = client.post(
        f"/api/v1/jobs/{job_id}/stages",
        json={"name": "System Architecture", "position": 3},
    )
    assert response.status_code == 201
    data = response.json()["data"]
    assert data["name"] == "System Architecture"
    assert data["position"] == 3


def test_delete_job_pipeline_stage_endpoint_success(
    client: TestClient,
    mock_job_service: AsyncMock,
) -> None:
    """Verify DELETE /api/v1/jobs/{job_id}/stages/{stage_id} returns 204 No Content."""
    job_id = uuid.uuid4()
    stage_id = uuid.uuid4()
    mock_job_service.delete_pipeline_stage.return_value = True

    response = client.delete(f"/api/v1/jobs/{job_id}/stages/{stage_id}")
    assert response.status_code == 204
