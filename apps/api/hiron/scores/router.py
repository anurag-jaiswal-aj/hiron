"""Thin FastAPI router for Score domain per API Contract §SCORE-1..5."""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.scores.schemas import (
    BatchScoreRequest,
    BatchScoreResponse,
    ScoreExplanationResponse,
    ScoreHistoryResponse,
    ScoreResponse,
)
from hiron.scores.service import ScoreService
from hiron.users.models import User

router = APIRouter(tags=["AI Scoring"])


def get_score_service() -> ScoreService:
    """Dependency provider for ScoreService."""
    return ScoreService()


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/score",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Score Candidate for Job (SCORE-1)",
)
async def score_candidate_endpoint(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    force_rescore: bool = Query(default=False, alias="forceRescore"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: ScoreService = Depends(get_score_service),
) -> ScoreResponse:
    """Trigger AI fit scoring for candidate against a job per API Contract §SCORE-1."""
    return await service.score_candidate_sync(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        job_id=job_id,
        candidate_id=candidate_id,
        force_rescore=force_rescore,
    )


@router.post(
    "/jobs/{job_id}/score-batch",
    response_model=BatchScoreResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Batch Score Candidates (SCORE-2)",
)
async def batch_score_candidates_endpoint(
    job_id: uuid.UUID,
    request: BatchScoreRequest | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: ScoreService = Depends(get_score_service),
) -> BatchScoreResponse:
    """Score all unscored candidates for a job in async batch per API Contract §SCORE-2."""
    candidate_ids = request.candidate_ids if request else None
    force_rescore = request.force_rescore if request else False
    return await service.batch_score_async(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        job_id=job_id,
        candidate_ids=candidate_ids,
        force_rescore=force_rescore,
    )


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/score",
    response_model=ScoreResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Score (SCORE-3)",
)
async def get_score_endpoint(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: ScoreService = Depends(get_score_service),
) -> ScoreResponse:
    """Fetch current active score for candidate-job pair per API Contract §SCORE-3."""
    return await service.get_score(
        session=session,
        tenant_id=current_user.tenant_id,
        job_id=job_id,
        candidate_id=candidate_id,
    )


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/scores/history",
    response_model=ScoreHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Score History (SCORE-4)",
)
async def get_score_history_endpoint(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: ScoreService = Depends(get_score_service),
) -> ScoreHistoryResponse:
    """Fetch historical scores for candidate-job pair per API Contract §SCORE-4."""
    return await service.get_score_history(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        job_id=job_id,
        candidate_id=candidate_id,
    )


@router.get(
    "/scores/{score_id}/explanation",
    response_model=ScoreExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Score Explanation (SCORE-5)",
)
async def get_score_explanation_endpoint(
    score_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: ScoreService = Depends(get_score_service),
) -> ScoreExplanationResponse:
    """Fetch full AI-generated score explanation and confidence factors per API Contract §SCORE-5."""
    return await service.get_score_explanation(
        session=session,
        tenant_id=current_user.tenant_id,
        score_id=score_id,
    )
