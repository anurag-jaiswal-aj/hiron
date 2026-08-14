"""QStash Webhook routing."""

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.common.exceptions import ResourceNotFoundException
from hiron.core.database import get_db_session
from hiron.embeddings.schemas import CandidateEmbeddingWebhookPayload, JobEmbeddingWebhookPayload
from hiron.embeddings.service import EmbeddingService
from hiron.scores.schemas import BatchScoreWorkerWebhookPayload
from hiron.scores.service import ScoreService
from hiron.webhooks.qstash_auth import verify_qstash_signature

logger = structlog.get_logger("hiron.webhooks.router")

router = APIRouter()


class TestWebhookPayload(BaseModel):
    hello: str


class TestWebhookRequest(BaseModel):
    event: str
    message_id: str
    payload: TestWebhookPayload


@router.post("/qstash/test", dependencies=[Depends(verify_qstash_signature)])
async def qstash_test_webhook(request: Request) -> dict[str, str]:
    """Test webhook endpoint for QStash signature verification.

    Raw request body is read and authenticated via `verify_qstash_signature` dependency.
    After successful authentication, the body is parsed as JSON.
    """
    body_bytes = await request.body()
    try:
        parsed = TestWebhookRequest.model_validate_json(body_bytes)
    except ValidationError as e:
        logger.warning("Malformed JSON in webhook", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Malformed payload",
        )

    logger.info("Received authenticated QStash test webhook", message_id=parsed.message_id)

    return {
        "status": "accepted",
        "event": parsed.event,
    }


from typing import Any


@router.post("/qstash/embeddings/candidate", dependencies=[Depends(verify_qstash_signature)])
async def qstash_candidate_embedding_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Webhook to execute candidate embedding generation."""
    body_bytes = await request.body()
    try:
        parsed = CandidateEmbeddingWebhookPayload.model_validate_json(body_bytes)
    except ValidationError as e:
        logger.warning("Malformed JSON in candidate embedding webhook", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Malformed payload",
        )

    tenant_id = parsed.tenant_id
    candidate_id = parsed.candidate_id

    service = EmbeddingService()

    try:
        result = await service.generate_candidate_embedding_pipeline(
            session=session,
            tenant_id=tenant_id,
            candidate_id=candidate_id,
            model_version=parsed.model_version,
        )

        if result.status == "failed" and result.error_type == "rate_limit":
            # Throw 429 so QStash retries
            raise HTTPException(status_code=429, detail="AI Provider rate limit exceeded")

        logger.info("ABOUT TO CALL session.commit()")
        await session.commit()
        logger.info("FINISHED CALLING session.commit()")

        return {"status": "success", "cache_hit": result.cache_hit}

    except Exception as e:
        logger.error("Failed to generate candidate embedding via webhook", error=str(e))
        # Reraise so QStash handles retries based on status code
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qstash/embeddings/job", dependencies=[Depends(verify_qstash_signature)])
async def qstash_job_embedding_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Webhook to execute job embedding generation."""
    body_bytes = await request.body()
    try:
        parsed = JobEmbeddingWebhookPayload.model_validate_json(body_bytes)
    except ValidationError as e:
        logger.warning("Malformed JSON in job embedding webhook", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Malformed payload",
        )

    tenant_id = parsed.tenant_id
    job_id = parsed.job_id

    service = EmbeddingService()

    try:
        result = await service.generate_job_embedding_pipeline(
            session=session,
            tenant_id=tenant_id,
            job_id=job_id,
            model_version=parsed.model_version,
        )

        if result.status == "failed" and result.error_type == "rate_limit":
            # Throw 429 so QStash retries
            raise HTTPException(status_code=429, detail="AI Provider rate limit exceeded")

        await session.commit()

        return {"status": "success", "cache_hit": result.cache_hit}

    except Exception as e:
        logger.error("Failed to generate job embedding via webhook", error=str(e))
        # Reraise so QStash handles retries based on status code
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/qstash/scores/batch/worker", dependencies=[Depends(verify_qstash_signature)])
async def qstash_batch_score_worker_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Webhook to execute individual candidate scoring in a batch."""
    body_bytes = await request.body()
    try:
        parsed = BatchScoreWorkerWebhookPayload.model_validate_json(body_bytes)
    except ValidationError as e:
        logger.warning("Malformed JSON in batch score worker webhook", error=str(e))
        return {"status": "failed", "reason": "Malformed payload", "details": str(e)}

    service = ScoreService()

    try:
        # We pass user_role="org_admin" because this is a trusted system action via QStash signature
        await service.score_candidate_sync(
            session=session,
            tenant_id=parsed.tenant_id,
            user_role="org_admin",
            job_id=parsed.job_id,
            candidate_id=parsed.candidate_id,
            force_rescore=parsed.force_rescore,
        )

        # Successful terminal claim
        claimed = await service.score_repo.claim_batch_score_worker_success(
            session=session,
            tenant_id=parsed.tenant_id,
            batch_id=parsed.batch_id,
            candidate_id=parsed.candidate_id,
        )
        if not claimed:
            logger.info(
                "Worker success ignored: candidate already terminally claimed",
                batch_id=parsed.batch_id,
                candidate_id=str(parsed.candidate_id),
            )

        await session.commit()

        return {
            "status": "success",
            "batch_id": parsed.batch_id,
            "candidate_id": str(parsed.candidate_id),
        }

    except Exception as e:
        logger.error("Failed to score candidate via webhook worker", error=str(e))

        # We must map exceptions according to ERROR_MATRIX.md
        if isinstance(e, ResourceNotFoundException):
            # Invalid UUID / Entity Not Found -> 200 OK (Ack)
            await service.score_repo.claim_batch_score_worker_failure(
                session=session,
                tenant_id=parsed.tenant_id,
                batch_id=parsed.batch_id,
                candidate_id=parsed.candidate_id,
            )
            await session.commit()
            return {"status": "ignored", "reason": "Entity not found", "details": str(e)}

        if isinstance(e, httpx.HTTPStatusError):
            if e.response.status_code == 429:
                # Quota limit -> 429 Too Many Requests -> QStash retries
                raise HTTPException(status_code=429, detail="AI Provider rate limit exceeded")
            if e.response.status_code >= 500:
                # AI Internal Error / Bad Gateway -> 503 Service Unavailable -> QStash retries
                raise HTTPException(status_code=503, detail="AI Provider transient error")

            # AI Schema Error / 400 Bad Request -> 200 OK (Ack)
            await service.score_repo.claim_batch_score_worker_failure(
                session=session,
                tenant_id=parsed.tenant_id,
                batch_id=parsed.batch_id,
                candidate_id=parsed.candidate_id,
            )
            await session.commit()
            return {"status": "failed", "reason": "Terminal AI error", "details": str(e)}

        import pydantic

        if isinstance(e, pydantic.ValidationError):
            # AI returned bad JSON schema -> 200 OK (Ack)
            await service.score_repo.claim_batch_score_worker_failure(
                session=session,
                tenant_id=parsed.tenant_id,
                batch_id=parsed.batch_id,
                candidate_id=parsed.candidate_id,
            )
            await session.commit()
            return {"status": "failed", "reason": "AI Schema Error", "details": str(e)}

        # Reraise so QStash handles retries based on status code
        if isinstance(e, HTTPException):
            raise

        # All other unhandled exceptions: 500 -> QStash retries
        raise HTTPException(status_code=500, detail=str(e))


from hiron.core.config import get_settings
from hiron.core.qstash_client import qstash_publisher
from hiron.scores.schemas import BatchScoreCoordinatorWebhookPayload


@router.post("/qstash/scores/batch/coordinator", dependencies=[Depends(verify_qstash_signature)])
async def qstash_batch_score_coordinator_webhook(
    request: Request,
    session: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Webhook to coordinate fan-out for batch candidate scoring."""
    body_bytes = await request.body()
    try:
        parsed = BatchScoreCoordinatorWebhookPayload.model_validate_json(body_bytes)
    except ValidationError as e:
        logger.warning("Malformed JSON in batch score coordinator webhook", error=str(e))
        return {"status": "failed", "reason": "Malformed payload", "details": str(e)}

    service = ScoreService()
    batch_job = await service.score_repo.get_batch_score_job(
        session=session, tenant_id=parsed.tenant_id, batch_id=parsed.batch_id
    )

    if not batch_job:
        logger.warning("Batch job not found for coordinator", batch_id=parsed.batch_id)
        return {"status": "ignored", "reason": "Batch job not found"}

    if batch_job.status in ("completed", "failed"):
        logger.info(
            "Batch job already completed or failed, ignoring duplicate delivery",
            batch_id=parsed.batch_id,
            status=batch_job.status,
        )
        return {"status": "ignored", "reason": "Already terminal"}

    # Zero candidate behavior
    if batch_job.queued_count == 0 or len(parsed.candidate_ids) == 0:
        batch_job.status = "completed"
        batch_job.completed_count = 0
        batch_job.failed_count = 0
        batch_job.queued_count = 0
        await session.flush()
        return {"status": "completed", "reason": "Zero candidates"}

    if batch_job.status == "pending":
        rowcount = await service.score_repo.transition_batch_score_job_to_processing(
            session=session, tenant_id=parsed.tenant_id, batch_id=parsed.batch_id
        )
        if rowcount == 0:
            logger.info(
                "Batch already transitioned to processing concurrently", batch_id=parsed.batch_id
            )

    # Fan out to workers using candidate_ids from payload (immutable snapshot)
    settings = get_settings()
    if not settings.qstash_webhook_url:
        raise HTTPException(status_code=500, detail="QStash webhook URL not configured")

    # Commit the transaction so workers see the status as processing
    await session.commit()

    # Gather promises for the publish_json calls
    for candidate_id in parsed.candidate_ids:
        worker_payload = {
            "batch_id": parsed.batch_id,
            "tenant_id": str(parsed.tenant_id),
            "job_id": str(parsed.job_id),
            "candidate_id": str(candidate_id),
            "force_rescore": parsed.force_rescore,
        }
        dedup_id = (
            f"batch-worker-{parsed.tenant_id}-{parsed.job_id}-{candidate_id}-{parsed.batch_id}"
        )

        try:
            await qstash_publisher.publish(
                url=f"{settings.qstash_webhook_url}/api/v1/webhooks/qstash/scores/batch/worker",
                payload=worker_payload,
                deduplication_id=dedup_id,
            )
        except Exception as e:
            logger.error(
                "Failed to publish to QStash worker",
                batch_id=parsed.batch_id,
                candidate_id=str(candidate_id),
                error=str(e),
            )
            # Don't update batch counters, let QStash retry the coordinator
            raise HTTPException(
                status_code=500, detail=f"Failed to enqueue worker for {candidate_id}"
            )

    return {"status": "processing", "fan_out_count": len(parsed.candidate_ids)}
