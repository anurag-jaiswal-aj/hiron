from typing import Any
import uuid

from fastapi import Depends, FastAPI, Request
import structlog
from pydantic import BaseModel

from hiron.core.database import AsyncSessionLocal
from hiron.security.context import set_tenant_context
from hiron.webhooks.qstash_auth import verify_qstash_signature

from apps.worker.src.pipeline import parse_resume_pipeline
from apps.worker.src.embeddings import (
    generate_candidate_embedding_worker_pipeline,
    generate_job_embedding_worker_pipeline,
)

logger = structlog.get_logger("hiron.worker.main")

app = FastAPI(title="Hiron Worker API")


class ParseResumePayload(BaseModel):
    tenant_id: uuid.UUID
    resume_id: uuid.UUID


class CandidateEmbeddingPayload(BaseModel):
    tenant_id: uuid.UUID
    candidate_id: uuid.UUID
    model_version: str


class JobEmbeddingPayload(BaseModel):
    tenant_id: uuid.UUID
    job_id: uuid.UUID
    model_version: str


@app.get("/health")
async def health_check():
    """Minimal health endpoint."""
    return {"status": "ok"}


@app.post("/api/v1/webhooks/qstash/resumes/parse", dependencies=[Depends(verify_qstash_signature)])
async def parse_resume_webhook(payload: ParseResumePayload) -> dict[str, str]:
    """QStash webhook endpoint for resume parsing."""
    logger.info("Received resume parse request", tenant_id=str(payload.tenant_id), resume_id=str(payload.resume_id))

    set_tenant_context(payload.tenant_id)

    async with AsyncSessionLocal() as session:
        try:
            await parse_resume_pipeline(
                session=session,
                tenant_id=payload.tenant_id,
                resume_id=payload.resume_id,
            )
            return {"status": "parsed"}
        except Exception as exc:
            # Re-raise so QStash knows it failed and can retry if it's transient.
            logger.error("Error in parse_resume_webhook", error=str(exc))
            raise


@app.post("/api/v1/webhooks/qstash/embeddings/candidate", dependencies=[Depends(verify_qstash_signature)])
async def generate_candidate_embedding_webhook(payload: CandidateEmbeddingPayload) -> dict[str, str]:
    """QStash webhook endpoint for candidate embedding generation."""
    logger.info("Received candidate embedding request", tenant_id=str(payload.tenant_id), candidate_id=str(payload.candidate_id))

    set_tenant_context(payload.tenant_id)

    async with AsyncSessionLocal() as session:
        try:
            await generate_candidate_embedding_worker_pipeline(
                session=session,
                tenant_id=payload.tenant_id,
                candidate_id=payload.candidate_id,
            )
            return {"status": "success"}
        except Exception as exc:
            logger.error("Error in generate_candidate_embedding_webhook", error=str(exc))
            raise


@app.post("/api/v1/webhooks/qstash/embeddings/job", dependencies=[Depends(verify_qstash_signature)])
async def generate_job_embedding_webhook(payload: JobEmbeddingPayload) -> dict[str, str]:
    """QStash webhook endpoint for job embedding generation."""
    logger.info("Received job embedding request", tenant_id=str(payload.tenant_id), job_id=str(payload.job_id))

    set_tenant_context(payload.tenant_id)

    async with AsyncSessionLocal() as session:
        try:
            await generate_job_embedding_worker_pipeline(
                session=session,
                tenant_id=payload.tenant_id,
                job_id=payload.job_id,
            )
            return {"status": "success"}
        except Exception as exc:
            logger.error("Error in generate_job_embedding_webhook", error=str(exc))
            raise


from hiron.webhooks.router import (
    qstash_batch_score_coordinator_webhook,
    qstash_batch_score_worker_webhook,
)

app.add_api_route(
    "/api/v1/webhooks/qstash/scores/batch/coordinator",
    endpoint=qstash_batch_score_coordinator_webhook,
    methods=["POST"],
    dependencies=[Depends(verify_qstash_signature)],
)

app.add_api_route(
    "/api/v1/webhooks/qstash/scores/batch/worker",
    endpoint=qstash_batch_score_worker_webhook,
    methods=["POST"],
    dependencies=[Depends(verify_qstash_signature)],
)
