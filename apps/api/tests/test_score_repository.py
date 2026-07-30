"""Unit tests for ScoreRepository creation, active score demotion, and history queries."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from hiron.scores.models import Score
from hiron.scores.repository import ScoreRepository


@pytest.mark.asyncio
async def test_create_score_demotes_previous_current_score() -> None:
    """Verify create_score executes update to demote previous active score to is_current=False."""
    repo = ScoreRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_candidate_id = uuid.uuid4()

    mock_result = MagicMock()
    session.execute = AsyncMock(return_value=mock_result)

    score = await repo.create_score(
        session=session,
        tenant_id=tenant_id,
        job_candidate_id=job_candidate_id,
        fit_score=88,
        confidence=0.90,
        breakdown={"skills": {"score": 90, "weight": 0.4, "details": "good"}},
        explanation="Strong candidate",
        skills_matched=["Python"],
        skills_missing=[],
        prompt_name="candidate_fit_scoring",
        prompt_version="2.0.0",
        model_version="gpt-4o-2024-08-06",
    )

    assert score.tenant_id == tenant_id
    assert score.fit_score == 88
    assert score.is_current is True
    session.execute.assert_called_once()
    session.add.assert_called_once()


@pytest.mark.asyncio
async def test_get_current_score_query() -> None:
    """Verify get_current_score queries for is_current=True score."""
    repo = ScoreRepository()
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    job_candidate_id = uuid.uuid4()

    mock_score = Score(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        job_candidate_id=job_candidate_id,
        fit_score=92,
        is_current=True,
    )
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_score
    session.execute = AsyncMock(return_value=mock_result)

    result = await repo.get_current_score(session, tenant_id, job_candidate_id)

    assert result is not None
    assert result.fit_score == 92
