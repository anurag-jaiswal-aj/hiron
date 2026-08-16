"""Thin FastAPI router for Pipeline domain per API Contract §PIPE-1..4."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.pipeline.schemas import (
    MoveCandidateStageRequest,
    MoveCandidateStageResponse,
    PipelineBoardResponse,
    RejectCandidateRequest,
    RejectCandidateResponse,
    ShortlistCandidateResponse,
    StageHistoryResponse,
)
from hiron.pipeline.service import PipelineService
from hiron.users.models import User

router = APIRouter(tags=["Pipeline"])


def get_pipeline_service() -> PipelineService:
    """Dependency provider for PipelineService."""
    return PipelineService()


@router.post(
    "/pipeline/move",
    response_model=MoveCandidateStageResponse,
    status_code=status.HTTP_200_OK,
    summary="Move Candidate Stage (PIPE-1)",
)
async def move_candidate_stage_endpoint(
    request: MoveCandidateStageRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: PipelineService = Depends(get_pipeline_service),
) -> MoveCandidateStageResponse:
    """Move a candidate to a different stage in their job pipeline (Kanban drag-and-drop) per §PIPE-1."""
    return await service.move_candidate_stage(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        job_candidate_id=request.job_candidate_id,
        to_stage_id=request.to_stage_id,
        note=request.note,
    )


@router.get(
    "/jobs/{job_id}/candidates/{candidate_id}/stage-history",
    response_model=StageHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Stage History (PIPE-2)",
)
async def get_stage_history_endpoint(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: PipelineService = Depends(get_pipeline_service),
) -> StageHistoryResponse:
    """Get complete stage transition history (timeline) for a candidate in a job per §PIPE-2."""
    return await service.get_stage_history(
        session=session,
        tenant_id=current_user.tenant_id,
        job_id=job_id,
        candidate_id=candidate_id,
    )


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/shortlist",
    response_model=ShortlistCandidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Shortlist Candidate (PIPE-3)",
)
async def shortlist_candidate_endpoint(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: PipelineService = Depends(get_pipeline_service),
) -> ShortlistCandidateResponse:
    """Mark a candidate as shortlisted for hiring manager review per §PIPE-3."""
    return await service.shortlist_candidate(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        job_id=job_id,
        candidate_id=candidate_id,
    )


@router.post(
    "/jobs/{job_id}/candidates/{candidate_id}/reject",
    response_model=RejectCandidateResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject Candidate (PIPE-4)",
)
async def reject_candidate_endpoint(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    request: RejectCandidateRequest | None = None,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: PipelineService = Depends(get_pipeline_service),
) -> RejectCandidateResponse:
    """Move a candidate to the rejected stage with a reason per §PIPE-4."""
    reason = request.reason if request else None
    return await service.reject_candidate(
        session=session,
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        user_role=current_user.role,
        job_id=job_id,
        candidate_id=candidate_id,
        reason=reason,
    )


@router.get(
    "/jobs/{job_id}/pipeline",
    response_model=PipelineBoardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Pipeline Board",
)
async def get_pipeline_board_endpoint(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: PipelineService = Depends(get_pipeline_service),
) -> PipelineBoardResponse:
    """Get Kanban pipeline board with candidate cards, counts, and AI scores."""
    return await service.get_pipeline_board(
        session=session,
        tenant_id=current_user.tenant_id,
        job_id=job_id,
    )
