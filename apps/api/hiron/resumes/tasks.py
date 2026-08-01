"""Async Celery background tasks for resume parsing pipeline execution."""

import asyncio
import uuid

import structlog

from hiron.core.celery import celery_app
from hiron.core.database import AsyncSessionLocal
from hiron.resumes.repository import ResumeRepository
from hiron.resumes.service import ResumeService

logger = structlog.get_logger("hiron.resumes.tasks")


async def _async_parse_resume_task(tenant_id: str, resume_id: str) -> dict[str, str]:
    """Internal async execution logic for resume parsing task."""
    t_uuid = uuid.UUID(tenant_id)
    r_uuid = uuid.UUID(resume_id)
    service = ResumeService()

    async with AsyncSessionLocal() as session:
        try:
            await service.parse_resume_pipeline(
                session=session,
                tenant_id=t_uuid,
                resume_id=r_uuid,
            )
            await session.commit()
            logger.info(
                "Resume parsing background task completed successfully",
                tenant_id=tenant_id,
                resume_id=resume_id,
            )
            return {"status": "success", "resume_id": resume_id}
        except Exception as exc:
            logger.error(
                "Resume parsing background task failed",
                tenant_id=tenant_id,
                resume_id=resume_id,
                error=str(exc),
            )
            await session.rollback()

            # Open a fresh session to ensure failed status update is committed to database
            try:
                async with AsyncSessionLocal() as fail_session:
                    repo = ResumeRepository()
                    fail_resume = await repo.get_resume_by_id(
                        session=fail_session,
                        tenant_id=t_uuid,
                        resume_id=r_uuid,
                    )
                    if fail_resume:
                        await repo.update_resume_status(
                            session=fail_session,
                            resume=fail_resume,
                            status="failed",
                            parse_error=str(exc),
                        )
                        await fail_session.commit()
            except Exception as persist_exc:
                logger.error(
                    "Failed to persist failure status for resume",
                    tenant_id=tenant_id,
                    resume_id=resume_id,
                    error=str(persist_exc),
                )
            raise


@celery_app.task(name="hiron.resumes.parse_resume")  # type: ignore[untyped-decorator]
def parse_resume(tenant_id: str, resume_id: str) -> dict[str, str]:
    """Registered Celery background task for resume parsing per Architecture §10."""
    return asyncio.run(_async_parse_resume_task(tenant_id=tenant_id, resume_id=resume_id))
