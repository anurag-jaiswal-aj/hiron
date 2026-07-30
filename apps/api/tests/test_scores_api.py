"""API integration tests for SCORE-1 through SCORE-5 endpoints."""

import datetime
import uuid
from collections.abc import Generator
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.main import create_app
from hiron.scores.router import get_score_service
from hiron.scores.schemas import (
    BatchScoreData,
    BatchScoreResponse,
    ConfidenceFactorsData,
    ScoreData,
    ScoreExplanationData,
    ScoreExplanationResponse,
    ScoreHistoryItem,
    ScoreHistoryResponse,
    ScoreResponse,
)
from hiron.users.models import User

app = create_app()


@pytest.fixture
def mock_score_service() -> AsyncMock:
    """Fixture supplying mock ScoreService."""
    return AsyncMock()


@pytest.fixture
def client(mock_score_service: AsyncMock) -> Generator[TestClient, None, None]:
    """TestClient fixture overriding user context and ScoreService dependencies."""
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
    app.dependency_overrides[get_score_service] = lambda: mock_score_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_score_candidate_endpoint_success(
    client: TestClient, mock_score_service: AsyncMock
) -> None:
    """Verify POST /api/v1/jobs/{job_id}/candidates/{candidate_id}/score returns 200 OK per §SCORE-1."""
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()
    score_id = uuid.uuid4()

    mock_score_service.score_candidate_sync.return_value = ScoreResponse(
        data=ScoreData(
            id=score_id,
            fit_score=92,
            confidence=0.87,
            breakdown={"skills": {"score": 88, "weight": 0.4, "details": "matched"}},
            explanation="Jane Smith is a strong match",
            skills_matched=["Python"],
            skills_missing=[],
            warnings=[],
            prompt_version="2.0.0",
            model_version="gpt-4o-2024-08-06",
            is_current=True,
            created_at=datetime.datetime.now(datetime.UTC),
        )
    )

    response = client.post(f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/score")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["fitScore"] == 92
    assert res_data["id"] == str(score_id)


def test_batch_score_endpoint_success(client: TestClient, mock_score_service: AsyncMock) -> None:
    """Verify POST /api/v1/jobs/{job_id}/score-batch returns 202 Accepted per §SCORE-2."""
    job_id = uuid.uuid4()

    mock_score_service.batch_score_async.return_value = BatchScoreResponse(
        data=BatchScoreData(
            task_id="task-123",
            candidates_queued=5,
            estimated_completion_seconds=25,
            status_url="/api/v1/tasks/task-123",
        )
    )

    response = client.post(f"/api/v1/jobs/{job_id}/score-batch")

    assert response.status_code == 202
    res_data = response.json()["data"]
    assert res_data["candidatesQueued"] == 5


def test_get_score_history_endpoint_success(
    client: TestClient, mock_score_service: AsyncMock
) -> None:
    """Verify GET /api/v1/jobs/{job_id}/candidates/{candidate_id}/scores/history returns 200 OK per §SCORE-4."""
    job_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    mock_score_service.get_score_history.return_value = ScoreHistoryResponse(
        data=[
            ScoreHistoryItem(
                id=uuid.uuid4(),
                fit_score=92,
                prompt_version="2.0.0",
                is_current=True,
                created_at=datetime.datetime.now(datetime.UTC),
            )
        ]
    )

    response = client.get(f"/api/v1/jobs/{job_id}/candidates/{candidate_id}/scores/history")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert len(res_data) == 1
    assert res_data[0]["fitScore"] == 92


def test_get_score_explanation_endpoint_success(
    client: TestClient, mock_score_service: AsyncMock
) -> None:
    """Verify GET /api/v1/scores/{score_id}/explanation returns 200 OK per §SCORE-5."""
    score_id = uuid.uuid4()

    mock_score_service.get_score_explanation.return_value = ScoreExplanationResponse(
        data=ScoreExplanationData(
            score_id=score_id,
            fit_score=92,
            explanation="Jane Smith is a strong match...",
            breakdown={},
            skills_matched=["Python"],
            skills_missing=[],
            warnings=[],
            confidence=0.87,
            confidence_factors=ConfidenceFactorsData(
                resume_completeness=0.95,
                output_consistency=0.90,
                explanation_quality=0.85,
                sanity_check_passed=True,
            ),
        )
    )

    response = client.get(f"/api/v1/scores/{score_id}/explanation")

    assert response.status_code == 200
    res_data = response.json()["data"]
    assert res_data["scoreId"] == str(score_id)
    assert res_data["confidenceFactors"]["sanityCheckPassed"] is True
