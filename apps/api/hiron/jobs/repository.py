"""Job repository providing tenant-isolated persistence operations for jobs and pipeline stages."""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql.elements import ColumnElement

from hiron.jobs.models import Job, PipelineStage


class JobRepository:
    """Repository managing Database CRUD operations for Job and PipelineStage entities."""

    async def create_job(
        self,
        session: AsyncSession,
        job: Job,
    ) -> Job:
        """Persist a new Job entity to the database."""
        session.add(job)
        await session.flush()
        return job

    async def get_job_by_id(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Job | None:
        """Fetch job by primary key ID and tenant_id with pipeline stages loaded."""
        stmt = (
            select(Job)
            .options(selectinload(Job.pipeline_stages))
            .where(
                Job.id == job_id,
                Job.tenant_id == tenant_id,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    def _build_job_order_by(self, sort: str) -> ColumnElement[Any]:
        """Map sort parameter string to SQLAlchemy ColumnElement."""
        sort_map: dict[str, ColumnElement[Any]] = {
            "createdAt:asc": Job.created_at.asc(),
            "createdAt:desc": Job.created_at.desc(),
            "title:asc": Job.title.asc(),
            "title:desc": Job.title.desc(),
            "status:asc": Job.status.asc(),
            "status:desc": Job.status.desc(),
            "openedAt:asc": Job.opened_at.asc(),
            "openedAt:desc": Job.opened_at.desc(),
        }
        return sort_map.get(sort, Job.created_at.desc())

    async def list_jobs(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        status: str | list[str] | None = None,
        department: str | None = None,
        q: str | None = None,
        include_archived: bool = False,
        sort: str = "createdAt:desc",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[Sequence[Job], int]:
        """List tenant jobs with optional status/department filters, full-text search, sorting, and pagination."""
        base_filters = [Job.tenant_id == tenant_id]

        if not include_archived:
            base_filters.append(Job.is_archived.is_(False))

        if status:
            status_list = (
                [s.strip() for s in status.split(",") if s.strip()]
                if isinstance(status, str)
                else status
            )
            if status_list:
                base_filters.append(Job.status.in_(status_list))

        if department:
            base_filters.append(Job.department == department.strip())

        if q and q.strip():
            base_filters.append(
                Job.search_vector.op("@@")(func.websearch_to_tsquery("english", q.strip()))
            )

        # Count total matching records
        count_stmt = select(func.count()).select_from(Job).where(*base_filters)
        count_res = await session.execute(count_stmt)
        total_count = int(count_res.scalar_one())

        order_clause = self._build_job_order_by(sort)

        items_stmt = (
            select(Job)
            .options(selectinload(Job.pipeline_stages))
            .where(*base_filters)
            .order_by(order_clause, Job.id.desc())
            .limit(limit)
            .offset(offset)
        )
        items_res = await session.execute(items_stmt)
        jobs = items_res.scalars().all()
        return jobs, total_count

    async def update_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
        **kwargs: Any,
    ) -> Job | None:
        """Update job fields for a tenant-isolated job entity."""
        job = await self.get_job_by_id(session, job_id, tenant_id)
        if not job:
            return None

        for key, value in kwargs.items():
            if hasattr(job, key) and value is not None:
                setattr(job, key, value)

        await session.flush()
        return job

    async def archive_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Job | None:
        """Mark a job as archived (soft delete)."""
        return await self.update_job(
            session=session,
            job_id=job_id,
            tenant_id=tenant_id,
            is_archived=True,
        )

    async def delete_job(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> bool:
        """Hard delete a job entity from the database."""
        job = await self.get_job_by_id(session, job_id, tenant_id)
        if not job:
            return False

        await session.delete(job)
        await session.flush()
        return True

    async def create_pipeline_stage(
        self,
        session: AsyncSession,
        stage: PipelineStage,
    ) -> PipelineStage:
        """Persist a single pipeline stage to the database."""
        session.add(stage)
        await session.flush()
        return stage

    async def create_pipeline_stages(
        self,
        session: AsyncSession,
        stages: Sequence[PipelineStage],
    ) -> Sequence[PipelineStage]:
        """Persist multiple pipeline stages in batch."""
        session.add_all(stages)
        await session.flush()
        return stages

    async def list_pipeline_stages(
        self,
        session: AsyncSession,
        job_id: uuid.UUID,
        tenant_id: uuid.UUID,
    ) -> Sequence[PipelineStage]:
        """List pipeline stages for a job ordered by position."""
        stmt = (
            select(PipelineStage)
            .where(
                PipelineStage.job_id == job_id,
                PipelineStage.tenant_id == tenant_id,
            )
            .order_by(PipelineStage.position.asc())
        )
        res = await session.execute(stmt)
        return res.scalars().all()
