"""API integration tests for PIPE-1 through PIPE-4 and Kanban board endpoints."""

import datetime
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.main import create_app
from hiron.pipeline.router import get_pipeline_service
from hiron.pipeline.schemas import (
    KanbanCandidateCard,
    MoveCandidateStageData,
    MoveCandidateStageResponse,
    PipelineBoardResponse,
    PipelineStageStats,
    RejectCandidateData,
    RejectCandidateResponse,
    ShortlistCandidateData,
    ShortlistCandidateResponse,
    StageHistoryItem,
    StageHistoryResponse,
    StageInfo,
    UserInfo,
)
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_pipeline_service() -> AsyncMock:
    """Fixture supplying mock PipelineService."""
    return AsyncMock()


@pytest.fixture
def client(mock_pipeline_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and PipelineService dependencies."""
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
    app.dependency_overrides[get_pipeline_service] = lambda: mock_pipeline_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_move_candidate_stage_endpoint_success(
    client: TestClient, mock_pipeline_service: AsyncMock
) -> None:
    """Verify POST /api/v1/pipeline/move returns 200 OK per API Contract §PIPE-1."""
    job_cand_id = uuid.uuid4()
    stage_id = uuid.uuid4()
    user_id = uuid.uuid4()

    mock_pipeline_service.move_candidate_stage.return_value = MoveCandidateStageResponse(
        data=MoveCandidateStageData(
            job_candidate_id=job_cand_id,
            previous_stage=StageInfo(id=uuid.uuid4(), name="Applied", position=1),
            current_stage=StageInfo(id=stage_id, name="Screening", position=2),
            moved_by=UserInfo(id=user_id, full_name="Jane Recruiter"),
            note="Passed resume screen",
            moved_at=datetime.datetime.now(datetime.UTC),
        )
    )

    response = client.post(
        "/api/v1/pipeline/move",
        json={
            "jobCandidateId": str(job_cand_id),
            "toStageId": str(stage_id),
            "note": "Passed resume screen",
        },
    )

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["jobCandidateId"] == str(job_cand_id)
    assert res_data["currentStage"]["name"] == "Screening"


def test_get_stage_history_endpoint_success(
    client: TestClient, mock_pipeline_service: AsyncMock
) -> None:
    """Verify GET /api/v1/jobs/{job_id}/candidates/{candidate_id}/stage-history returns 200 OK per §PIPE-2."""
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_pipeline_service.get_stage_history.return_value = StageHistoryResponse(
        data=[
            StageHistoryItem(
                id=uuid.uuid4(),
                from_stage=None,
                to_stage=StageInfo(id=uuid.uuid4(), name="Applied", position=1),
                moved_by=UserInfo(id=uuid.uuid4(), full_name="System"),
                note=None,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        ]
    )

    response = client.get(f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/stage-history")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert len(res_data) == 1
    assert res_data[0]["toStage"]["name"] == "Applied"


def test_shortlist_candidate_endpoint_success(
    client: TestClient, mock_pipeline_service: AsyncMock
) -> None:
    """Verify POST /api/v1/jobs/{job_id}/candidates/{candidate_id}/shortlist returns 200 OK per §PIPE-3."""
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    job_cand_id = uuid.uuid4()

    mock_pipeline_service.shortlist_candidate.return_value = ShortlistCandidateResponse(
        data=ShortlistCandidateData(
            job_candidate_id=job_cand_id,
            is_shortlisted=True,
            shortlisted_at=datetime.datetime.now(datetime.UTC),
        )
    )

    response = client.post(f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/shortlist")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["isShortlisted"] is True


def test_reject_candidate_endpoint_success(
    client: TestClient, mock_pipeline_service: AsyncMock
) -> None:
    """Verify POST /api/v1/jobs/{job_id}/candidates/{candidate_id}/reject returns 200 OK per §PIPE-4."""
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    job_cand_id = uuid.uuid4()

    mock_pipeline_service.reject_candidate.return_value = RejectCandidateResponse(
        data=RejectCandidateData(
            job_candidate_id=job_cand_id,
            status="rejected",
            rejection_reason="Insufficient experience",
            rejected_at=datetime.datetime.now(datetime.UTC),
        )
    )

    response = client.post(
        f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/reject",
        json={"reason": "Insufficient experience"},
    )

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["status"] == "rejected"
    assert res_data["rejectionReason"] == "Insufficient experience"


def test_get_pipeline_board_endpoint_success(
    client: TestClient, mock_pipeline_service: AsyncMock
) -> None:
    """Verify GET /api/v1/jobs/{job_id}/pipeline returns 200 OK with Kanban stage columns."""
    job_id = uuid.uuid4()
    stage_id = uuid.uuid4()

    mock_pipeline_service.get_pipeline_board.return_value = PipelineBoardResponse(
        data=[
            PipelineStageStats(
                stage_id=stage_id,
                stage_name="Screening",
                position=1,
                candidate_count=1,
                candidates=[
                    KanbanCandidateCard(
                        candidate_id=uuid.uuid4(),
                        job_candidate_id=uuid.uuid4(),
                        full_name="Jane Doe",
                        current_title="Senior Engineer",
                        fit_score=90,
                        confidence=0.88,
                        is_shortlisted=True,
                        applied_at=datetime.datetime.now(datetime.UTC),
                    )
                ],
            )
        ]
    )

    response = client.get(f"/api/v1/jobs/{job_id}/pipeline")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert len(res_data) == 1
    assert res_data[0]["stageName"] == "Screening"
    assert res_data[0]["candidateCount"] == 1
