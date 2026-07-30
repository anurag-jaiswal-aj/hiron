"""Async Celery background tasks for resume parsing pipeline execution."""

import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.resumes.service import ResumeService

logger = structlog.get_logger("hiron.resumes.tasks")


async def execute_resume_parse_task(
    session: AsyncSession,
    tenant_id: uuid.UUID,
    resume_id: uuid.UUID,
    resume_service: ResumeService | None = None,
) -> None:
    """Execute resume parsing pipeline task asynchronously."""
    service = resume_service or ResumeService()
    try:
        await service.parse_resume_pipeline(
            session=session,
            tenant_id=tenant_id,
            resume_id=resume_id,
        )
        logger.info(
            "Resume parsing background task completed successfully",
            tenant_id=str(tenant_id),
            resume_id=str(resume_id),
        )
    except Exception as exc:
        logger.error(
            "Resume parsing background task failed",
            tenant_id=str(tenant_id),
            resume_id=str(resume_id),
            error=str(exc),
        )
        raise
