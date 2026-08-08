"""Thin FastAPI router for Embedding domain per API Contract §EMBED-1..EMBED-3."""

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.embeddings.schemas import (
    EmbeddingStatusResponse,
    GenerateCandidateEmbeddingResponse,
    GenerateJobEmbeddingResponse,
    IndividualEmbeddingStatusResponse,
)
from hiron.embeddings.service import EmbeddingService
from hiron.users.models import User

router = APIRouter(tags=["Embeddings"])


def get_embedding_service() -> EmbeddingService:
    """Dependency provider for EmbeddingService."""
    return EmbeddingService()


@router.post(
    "/candidates/{candidate_id}/embedding",
    response_model=GenerateCandidateEmbeddingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Candidate Embedding (EMBED-1)",
)
async def generate_candidate_embedding_endpoint(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: EmbeddingService = Depends(get_embedding_service),
) -> GenerateCandidateEmbeddingResponse:
    """Generate (or regenerate) vector embedding for a candidate resume per API Contract §EMBED-1."""
    return await service.generate_candidate_embedding(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        candidate_id=candidate_id,
    )


@router.post(
    "/jobs/{job_id}/embedding",
    response_model=GenerateJobEmbeddingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Generate Job Embedding (EMBED-2)",
)
async def generate_job_embedding_endpoint(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: EmbeddingService = Depends(get_embedding_service),
) -> GenerateJobEmbeddingResponse:
    """Generate (or regenerate) vector embedding for a job description per API Contract §EMBED-2."""
    return await service.generate_job_embedding(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
        job_id=job_id,
    )


@router.get(
    "/embeddings/status",
    response_model=EmbeddingStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Tenant Embedding Status (EMBED-3)",
)
async def get_embedding_status_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: EmbeddingService = Depends(get_embedding_service),
) -> EmbeddingStatusResponse:
    """Check tenant embedding coverage statistics per API Contract §EMBED-3."""
    return await service.get_embedding_status(
        session=session,
        tenant_id=current_user.tenant_id,
        user_role=current_user.role,
    )


@router.get(
    "/embeddings/candidates/{candidate_id}",
    response_model=IndividualEmbeddingStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Candidate Embedding Status",
)
async def get_candidate_embedding_status_endpoint(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: EmbeddingService = Depends(get_embedding_service),
) -> IndividualEmbeddingStatusResponse:
    """Check individual candidate embedding status."""
    return await service.get_candidate_embedding_status(
        session=session,
        tenant_id=current_user.tenant_id,
        candidate_id=candidate_id,
    )


@router.get(
    "/embeddings/jobs/{job_id}",
    response_model=IndividualEmbeddingStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Job Embedding Status",
)
async def get_job_embedding_status_endpoint(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: EmbeddingService = Depends(get_embedding_service),
) -> IndividualEmbeddingStatusResponse:
    """Check individual job embedding status."""
    return await service.get_job_embedding_status(
        session=session,
        tenant_id=current_user.tenant_id,
        job_id=job_id,
    )
