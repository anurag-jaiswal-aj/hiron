"""Async background execution tasks for embedding generation."""

import asyncio
import uuid

import structlog

from hiron.core.celery import celery_app
from hiron.core.database import AsyncSessionLocal, engine
from hiron.embeddings.generator import DEFAULT_EMBEDDING_MODEL
from hiron.embeddings.service import EmbeddingService

logger = structlog.get_logger("hiron.embeddings.tasks")


async def _save_telemetry(
    tenant_id: uuid.UUID,
    operation: str,
    model_version: str,
    input_tokens: int,
    output_tokens: int,
    cost_usd: float,
    latency_ms: int,
    status: str,
    error_type: str | None,
    is_cache_hit: bool,
) -> None:
    """Save telemetry using an independent DB session."""
    try:
        async with AsyncSessionLocal() as telemetry_session:
            from hiron.ai_usage.repository import AIUsageRepository
            ai_repo = AIUsageRepository()
            await ai_repo.create_usage_log(
                session=telemetry_session,
                tenant_id=tenant_id,
                operation=operation,
                model_version=model_version,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                status=status,
                error_type=error_type,
                is_cache_hit=is_cache_hit,
            )
            await telemetry_session.commit()
    except Exception as exc:
        logger.error("Failed to write embedding telemetry", tenant_id=str(tenant_id), error=str(exc))


async def _async_generate_candidate_embedding_task(
    tenant_id: str,
    candidate_id: str,
    model_version: str,
) -> dict[str, str]:
    t_uuid = uuid.UUID(tenant_id)
    c_uuid = uuid.UUID(candidate_id)
    service = EmbeddingService()

    result = None
    exc_obj = None

    try:
        async with AsyncSessionLocal() as session:
            try:
                result = await service.generate_candidate_embedding_pipeline(
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
            except Exception as exc:
                exc_obj = exc
                logger.error(
                    "Candidate embedding task failed",
                    tenant_id=tenant_id,
                    candidate_id=candidate_id,
                    error=str(exc),
                )
                await session.rollback()

        if result:
            await _save_telemetry(
                tenant_id=t_uuid,
                operation="candidate_embedding",
                model_version=result.model_version,
                input_tokens=result.input_tokens,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=result.latency_ms,
                status=result.status,
                error_type=result.error_type,
                is_cache_hit=result.cache_hit,
            )
            if exc_obj:
                raise exc_obj
        elif exc_obj:
            await _save_telemetry(
                tenant_id=t_uuid,
                operation="candidate_embedding",
                model_version=model_version,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=0,
                status="error",
                error_type=exc_obj.__class__.__name__,
                is_cache_hit=False,
            )
            raise exc_obj
    finally:
        await engine.dispose()

    return {"status": "success", "candidate_id": candidate_id}


from asgiref.sync import async_to_sync

@celery_app.task(name="hiron.embeddings.generate_candidate_embedding")  # type: ignore[untyped-decorator]
def generate_candidate_embedding(
    tenant_id: str,
    candidate_id: str,
    model_version: str = DEFAULT_EMBEDDING_MODEL,
) -> dict[str, str]:
    """Registered Celery background task for candidate embedding generation."""
    return async_to_sync(_async_generate_candidate_embedding_task)(
        tenant_id=tenant_id,
        candidate_id=candidate_id,
        model_version=model_version,
    )


async def _async_generate_job_embedding_task(
    tenant_id: str,
    job_id: str,
    model_version: str,
) -> dict[str, str]:
    t_uuid = uuid.UUID(tenant_id)
    j_uuid = uuid.UUID(job_id)
    service = EmbeddingService()

    result = None
    exc_obj = None

    try:
        async with AsyncSessionLocal() as session:
            try:
                result = await service.generate_job_embedding_pipeline(
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
            except Exception as exc:
                exc_obj = exc
                logger.error(
                    "Job embedding task failed",
                    tenant_id=tenant_id,
                    job_id=job_id,
                    error=str(exc),
                )
                await session.rollback()

        if result:
            await _save_telemetry(
                tenant_id=t_uuid,
                operation="job_embedding",
                model_version=result.model_version,
                input_tokens=result.input_tokens,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=result.latency_ms,
                status=result.status,
                error_type=result.error_type,
                is_cache_hit=result.cache_hit,
            )
            if exc_obj:
                raise exc_obj
        elif exc_obj:
            await _save_telemetry(
                tenant_id=t_uuid,
                operation="job_embedding",
                model_version=model_version,
                input_tokens=0,
                output_tokens=0,
                cost_usd=0.0,
                latency_ms=0,
                status="error",
                error_type=exc_obj.__class__.__name__,
                is_cache_hit=False,
            )
            raise exc_obj
    finally:
        await engine.dispose()

    return {"status": "success", "job_id": job_id}


@celery_app.task(name="hiron.embeddings.generate_job_embedding")  # type: ignore[untyped-decorator]
def generate_job_embedding(
    tenant_id: str,
    job_id: str,
    model_version: str = DEFAULT_EMBEDDING_MODEL,
) -> dict[str, str]:
    """Registered Celery background task for job embedding generation."""
    return async_to_sync(_async_generate_job_embedding_task)(
        tenant_id=tenant_id,
        job_id=job_id,
        model_version=model_version,
    )
