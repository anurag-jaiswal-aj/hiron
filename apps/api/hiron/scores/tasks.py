"""Async background execution tasks for candidate scoring."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.scores.service import ScoreService

logger = structlog.get_logger("hiron.scores.tasks")


async def execute_batch_scoring_task(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    job_id: uuid.UUID,
    candidate_ids: list[uuid.UUID],
    force_rescore: bool = False,
    score_service: ScoreService | None = None,
) -> None:
    """Execute candidate batch scoring asynchronously."""
    service = score_service or ScoreService()
    for candidate_id in candidate_ids:
        try:
            await service.score_candidate_sync(
                session=session,
                tenant_id=tenant_id,
                user_role="recruiter",
                job_id=job_id,
                candidate_id=candidate_id,
                force_rescore=force_rescore,
            )
        except Exception as exc:
            logger.warning(
                "Batch scoring item failed",
                tenant_id=str(tenant_id),
                job_id=str(job_id),
                candidate_id=str(candidate_id),
                error=str(exc),
            )
