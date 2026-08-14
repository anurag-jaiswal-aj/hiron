"""Worker pipelines for embedding generation tasks."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.ai_usage.repository import AIUsageRepository
from hiron.embeddings.generator import DEFAULT_EMBEDDING_MODEL
from hiron.embeddings.service import EmbeddingService

logger = structlog.get_logger("hiron.worker.embeddings")


async def generate_candidate_embedding_worker_pipeline(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    candidate_id: uuid.UUID,
) -> None:
    """Execute candidate embedding generation and log telemetry."""
    service = EmbeddingService()
    
    result = await service.generate_candidate_embedding_pipeline(
        session=session,
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        model_version=DEFAULT_EMBEDDING_MODEL,
    )

    try:
        async with session.begin_nested():
            ai_repo = AIUsageRepository()
            await ai_repo.create_usage_log(
                session=session,
                tenant_id=tenant_id,
                operation="generate_candidate_embedding",
                model_version=result.model_version,
                input_tokens=result.input_tokens,
                output_tokens=max(0, result.total_tokens - result.input_tokens),
                cost_usd=0.0,
                latency_ms=result.latency_ms,
                status=result.status,
                error_type=result.error_type,
                is_cache_hit=result.cache_hit,
            )
    except Exception as log_exc:
        logger.warning(
            "Failed to write AI usage telemetry for candidate embedding",
            error=str(log_exc),
            candidate_id=str(candidate_id),
        )

    await session.commit()


async def generate_job_embedding_worker_pipeline(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
) -> None:
    """Execute job embedding generation and log telemetry."""
    service = EmbeddingService()
    
    result = await service.generate_job_embedding_pipeline(
        session=session,
        tenant_id=tenant_id,
        job_id=job_id,
        model_version=DEFAULT_EMBEDDING_MODEL,
    )

    try:
        async with session.begin_nested():
            ai_repo = AIUsageRepository()
            await ai_repo.create_usage_log(
                session=session,
                tenant_id=tenant_id,
                operation="generate_job_embedding",
                model_version=result.model_version,
                input_tokens=result.input_tokens,
                output_tokens=max(0, result.total_tokens - result.input_tokens),
                cost_usd=0.0,
                latency_ms=result.latency_ms,
                status=result.status,
                error_type=result.error_type,
                is_cache_hit=result.cache_hit,
            )
    except Exception as log_exc:
        logger.warning(
            "Failed to write AI usage telemetry for job embedding",
            error=str(log_exc),
            job_id=str(job_id),
        )

    await session.commit()
