"""Async background execution tasks for embedding generation."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.embeddings.generator import DEFAULT_EMBEDDING_MODEL
from hiron.embeddings.service import EmbeddingService

logger = structlog.get_logger("hiron.embeddings.tasks")


async def execute_candidate_embedding_task(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    candidate_id: uuid.UUID,
    model_version: str = DEFAULT_EMBEDDING_MODEL,
    embedding_service: EmbeddingService | None = None,
) -> None:
    """Execute candidate vector embedding generation background task."""
    service = embedding_service or EmbeddingService()
    try:
        await service.generate_candidate_embedding_pipeline(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            model_version=model_version,
        )
        logger.info(
            "Candidate embedding task completed",
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
        )
    except Exception as exc:
        logger.error(
            "Candidate embedding task failed",
            tenant_id=str(tenant_id),
            candidate_id=str(candidate_id),
            error=str(exc),
        )
        raise


async def execute_job_embedding_task(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    model_version: str = DEFAULT_EMBEDDING_MODEL,
    embedding_service: EmbeddingService | None = None,
) -> None:
    """Execute job vector embedding generation background task."""
    service = embedding_service or EmbeddingService()
    try:
        await service.generate_job_embedding_pipeline(
            session=session,
            tenant_id=tenant_id,
            job_id=job_id,
            model_version=model_version,
        )
        logger.info(
            "Job embedding task completed",
            tenant_id=str(tenant_id),
            job_id=str(job_id),
        )
    except Exception as exc:
        logger.error(
            "Job embedding task failed",
            tenant_id=str(tenant_id),
            job_id=str(job_id),
            error=str(exc),
        )
        raise
