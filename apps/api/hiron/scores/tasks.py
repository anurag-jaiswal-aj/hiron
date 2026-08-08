"""Async background execution tasks for candidate scoring."""

import asyncio
import uuid

import structlog

from hiron.core.celery import celery_app
from hiron.core.database import AsyncSessionLocal
from hiron.scores.service import ScoreService

logger = structlog.get_logger("hiron.scores.tasks")


async def _async_execute_batch_scoring_task(
    tenant_id: str,
    job_id: str,
    candidate_ids: list[str],
    force_rescore: bool,
    celery_task: celery_app.Task,
) -> dict[str, str]:
    t_uuid = uuid.UUID(tenant_id)
    j_uuid = uuid.UUID(job_id)
    c_uuids = [uuid.UUID(c) for c in candidate_ids]

    service = ScoreService()
    total = len(c_uuids)

    async with AsyncSessionLocal() as session:
        for i, candidate_id in enumerate(c_uuids):
            try:
                await service.score_candidate_sync(
                    session=session,
                    tenant_id=t_uuid,
                    user_role="recruiter",
                    job_id=j_uuid,
                    candidate_id=candidate_id,
                    force_rescore=force_rescore,
                )
                await session.commit()
            except Exception as exc:
                await session.rollback()
                logger.warning(
                    "Batch scoring item failed",
                    tenant_id=tenant_id,
                    job_id=job_id,
                    candidate_id=str(candidate_id),
                    error=str(exc),
                )

            # Update celery progress state
            current = i + 1
            percent = int((current / total) * 100) if total > 0 else 100
            celery_task.update_state(
                state="PROGRESS",
                meta={
                    "current": current,
                    "total": total,
                    "percent": percent,
                }
            )

    return {"status": "success", "job_id": str(job_id), "processed_count": str(total)}


@celery_app.task(bind=True, name="hiron.scores.execute_batch_scoring")  # type: ignore[untyped-decorator]
def execute_batch_scoring(
    self: celery_app.Task,
    tenant_id: str,
    job_id: str,
    candidate_ids: list[str],
    force_rescore: bool = False,
) -> dict[str, str]:
    """Registered Celery background task for candidate batch scoring."""
    return asyncio.run(
        _async_execute_batch_scoring_task(
            tenant_id=tenant_id,
            job_id=job_id,
            candidate_ids=candidate_ids,
            force_rescore=force_rescore,
            celery_task=self,
        )
    )
