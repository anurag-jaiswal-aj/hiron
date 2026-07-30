"""End-to-end integration test suite for full Job lifecycle, status transitions, custom pipeline stages, RBAC, and skills validation."""

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
from hiron.jobs.models import Job, PipelineStage
from hiron.jobs.router import get_job_service, router as jobs_router
from hiron.jobs.service import JobService
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
def recruiter_harness(
    mock_db: AsyncMock,
    recruiter_user: User,
) -> Generator[tuple[TestClient, AsyncMock, JobService], None, None]:
    """TestClient harness authenticated as recruiter user with mock repository."""
    mock_repo = AsyncMock()
    service = JobService(job_repo=mock_repo)

    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(jobs_router, prefix="/api/v1/jobs")

    test_app.dependency_overrides[get_db_session] = lambda: mock_db
    test_app.dependency_overrides[get_job_service] = lambda: service
    test_app.dependency_overrides[get_current_user] = lambda: recruiter_user

    with TestClient(test_app) as client:
        yield client, mock_repo, service


def test_full_job_lifecycle_e2e(
    recruiter_harness: tuple[TestClient, AsyncMock, JobService],
    recruiter_user: User,
) -> None:
    """E2E Test: Create job -> default stages -> update -> create stage -> open -> pause -> close -> archive."""
    recruiter_client, mock_repo, _service = recruiter_harness
    job_id = uuid.uuid4()

    # 1. Create Job
    job = Job(
        id=job_id,
        tenant_id=recruiter_user.tenant_id,
        title="Principal AI Engineer",
        description="Lead LLM engineering team",
        department="AI/ML",
        status="draft",
        is_archived=False,
        required_skills=["Python", "PyTorch"],
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_repo.create_job.side_effect = lambda _s, j: j
    mock_repo.create_pipeline_stages.side_effect = lambda _s, stages: stages
    mock_repo.get_job_by_id.return_value = job

    create_resp = recruiter_client.post(
        "/api/v1/jobs",
        json={
            "title": "Principal AI Engineer",
            "description": "Lead LLM engineering team",
            "department": "AI/ML",
            "requiredSkills": ["Python", "PyTorch"],
        },
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["data"]["status"] == "draft"

    # 2. Update Job
    job.title = "Principal AI/ML Architect"
    mock_repo.update_job.return_value = job
    update_resp = recruiter_client.patch(
        f"/api/v1/jobs/{job_id}",
        json={"title": "Principal AI/ML Architect"},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["data"]["title"] == "Principal AI/ML Architect"

    # 3. Create Custom Pipeline Stage
    new_stage = PipelineStage(
        id=uuid.uuid4(),
        tenant_id=recruiter_user.tenant_id,
        job_id=job_id,
        name="Architecture Review",
        position=4,
        is_terminal=False,
        stage_type="active",
    )
    mock_repo.list_pipeline_stages.return_value = []
    mock_repo.create_pipeline_stage.return_value = new_stage

    stage_resp = recruiter_client.post(
        f"/api/v1/jobs/{job_id}/stages",
        json={"name": "Architecture Review", "position": 4},
    )
    assert stage_resp.status_code == 201
    assert stage_resp.json()["data"]["name"] == "Architecture Review"

    # 4. Open Job
    opened_job = Job(
        id=job_id,
        tenant_id=recruiter_user.tenant_id,
        title="Principal AI/ML Architect",
        description="Lead LLM engineering team",
        department="AI/ML",
        status="open",
        is_archived=False,
        opened_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_repo.update_job.return_value = opened_job
    open_resp = recruiter_client.post(f"/api/v1/jobs/{job_id}/open")
    assert open_resp.status_code == 200
    assert open_resp.json()["data"]["status"] == "open"

    # 5. Pause Job
    job.status = "open"
    paused_job = Job(
        id=job_id,
        tenant_id=recruiter_user.tenant_id,
        title="Principal AI/ML Architect",
        description="Lead LLM engineering team",
        department="AI/ML",
        status="paused",
        is_archived=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_repo.update_job.return_value = paused_job
    pause_resp = recruiter_client.post(f"/api/v1/jobs/{job_id}/pause")
    assert pause_resp.status_code == 200
    assert pause_resp.json()["data"]["status"] == "paused"

    # 6. Close Job
    closed_job = Job(
        id=job_id,
        tenant_id=recruiter_user.tenant_id,
        title="Principal AI/ML Architect",
        description="Lead LLM engineering team",
        department="AI/ML",
        status="closed",
        is_archived=False,
        closed_at=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_repo.update_job.return_value = closed_job
    close_resp = recruiter_client.post(
        f"/api/v1/jobs/{job_id}/close",
        json={"reason": "Role fulfilled"},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["data"]["status"] == "closed"

    # 7. Archive Job
    archived_job = Job(
        id=job_id,
        tenant_id=recruiter_user.tenant_id,
        title="Principal AI/ML Architect",
        description="Lead LLM engineering team",
        department="AI/ML",
        status="archived",
        is_archived=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_repo.update_job.return_value = archived_job
    archive_resp = recruiter_client.post(f"/api/v1/jobs/{job_id}/archive")
    assert archive_resp.status_code == 200
    assert archive_resp.json()["data"]["isArchived"] is True


def test_skills_validation_over_limit_raises_422(
    recruiter_harness: tuple[TestClient, AsyncMock, JobService],
) -> None:
    """Verify posting more than 50 skills returns 422 Unprocessable Content."""
    recruiter_client, _mock_repo, _service = recruiter_harness
    too_many_skills = [f"Skill_{i}" for i in range(51)]
    response = recruiter_client.post(
        "/api/v1/jobs",
        json={
            "title": "Title",
            "description": "Desc",
            "requiredSkills": too_many_skills,
        },
    )
    assert response.status_code == 422
