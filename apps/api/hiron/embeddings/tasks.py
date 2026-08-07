"""Async background execution tasks for embedding generation."""

import asyncio
import uuid

import structlog

from hiron.core.celery import celery_app
from hiron.core.database import AsyncSessionLocal
from hiron.embeddings.generator import DEFAULT_EMBEDDING_MODEL
from hiron.embeddings.service import EmbeddingService

logger = structlog.get_logger("hiron.embeddings.tasks")


async def _async_generate_candidate_embedding_task(
    tenant_id: str,
    candidate_id: str,
    model_version: str,
) -> dict[str, str]:
    t_uuid = uuid.UUID(tenant_id)
    c_uuid = uuid.UUID(candidate_id)
    service = EmbeddingService()

    async with AsyncSessionLocal() as session:
        try:
            await service.generate_candidate_embedding_pipeline(
                session=session,
                tenant_id=t_uuid,
                candidate_id=c_uuid,
                model_version=model_version,
            )
            await session.commit()
            logger.info(
                "Candidate embedding task completed",
                tenant_id=tenant_id,
                candidate_id=candidate_id,
            )
            return {"status": "success", "candidate_id": candidate_id}
        except Exception as exc:
            logger.error(
                "Candidate embedding task failed",
                tenant_id=tenant_id,
                candidate_id=candidate_id,
                error=str(exc),
            )
            await session.rollback()
            raise


@celery_app.task(name="hiron.embeddings.generate_candidate_embedding")  # type: ignore[untyped-decorator]
def generate_candidate_embedding(
    tenant_id: str,
    candidate_id: str,
    model_version: str = DEFAULT_EMBEDDING_MODEL,
) -> dict[str, str]:
    """Registered Celery background task for candidate embedding generation."""
    return asyncio.run(
        _async_generate_candidate_embedding_task(
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            model_version=model_version,
        )
    )


async def _async_generate_job_embedding_task(
    tenant_id: str,
    job_id: str,
    model_version: str,
) -> dict[str, str]:
    t_uuid = uuid.UUID(tenant_id)
    j_uuid = uuid.UUID(job_id)
    service = EmbeddingService()

    async with AsyncSessionLocal() as session:
        try:
            await service.generate_job_embedding_pipeline(
                session=session,
                tenant_id=t_uuid,
                job_id=j_uuid,
                model_version=model_version,
            )
            await session.commit()
            logger.info(
                "Job embedding task completed",
                tenant_id=tenant_id,
                job_id=job_id,
            )
            return {"status": "success", "job_id": job_id}
        except Exception as exc:
            logger.error(
                "Job embedding task failed",
                tenant_id=tenant_id,
                job_id=job_id,
                error=str(exc),
            )
            await session.rollback()
            raise


@celery_app.task(name="hiron.embeddings.generate_job_embedding")  # type: ignore[untyped-decorator]
def generate_job_embedding(
    tenant_id: str,
    job_id: str,
    model_version: str = DEFAULT_EMBEDDING_MODEL,
) -> dict[str, str]:
    """Registered Celery background task for job embedding generation."""
    return asyncio.run(
        _async_generate_job_embedding_task(
            tenant_id=tenant_id,
            job_id=job_id,
            model_version=model_version,
        )
    )
