"""Pipeline repository managing stage transitions, history logging, and Kanban board queries per Database Design §5.13."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hiron.candidates.models import Candidate, JobCandidate
from hiron.jobs.models import PipelineStage
from hiron.pipeline.models import CandidateStageHistory
from hiron.scores.models import Score


class PipelineRepository:
    """Repository handling SQL persistence for candidate stage movements, history, and Kanban stats."""

    async def get_job_candidate_by_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_candidate_id: uuid.UUID,
    ) -> JobCandidate | None:
        """Fetch JobCandidate by ID with tenant isolation and eager loading."""
        stmt = (
            select(JobCandidate)
            .where(
                JobCandidate.tenant_id == tenant_id,
                JobCandidate.id == job_candidate_id,
            )
            .options(
                selectinload(JobCandidate.current_stage),
                selectinload(JobCandidate.candidate),
                selectinload(JobCandidate.job),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_stage_by_id(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        stage_id: uuid.UUID,
    ) -> PipelineStage | None:
        """Fetch PipelineStage by ID with tenant isolation."""
        stmt = select(PipelineStage).where(
            PipelineStage.tenant_id == tenant_id,
            PipelineStage.id == stage_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_stages_for_job(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
    ) -> list[PipelineStage]:
        """Fetch all PipelineStage rows for a job ordered by position ASC."""
        stmt = (
            select(PipelineStage)
            .where(
                PipelineStage.tenant_id == tenant_id,
                PipelineStage.job_id == job_id,
            )
            .order_by(PipelineStage.position.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def create_stage_history(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_candidate_id: uuid.UUID,
        from_stage_id: uuid.UUID | None,
        to_stage_id: uuid.UUID,
        moved_by: uuid.UUID | None,
        note: str | None = None,
    ) -> CandidateStageHistory:
        """Insert an immutable transition audit record into candidate_stage_history."""
        history = CandidateStageHistory(
            tenant_id=tenant_id,
            job_candidate_id=job_candidate_id,
            from_stage_id=from_stage_id,
            to_stage_id=to_stage_id,
            moved_by=moved_by,
            note=note,
        )
        session.add(history)
        await session.flush()
        return history

    async def update_job_candidate_stage(
        self,
        session: AsyncSession,
        job_candidate: JobCandidate,
        to_stage_id: uuid.UUID,
    ) -> JobCandidate:
        """Update current_stage_id on job_candidate."""
        job_candidate.current_stage_id = to_stage_id
        await session.flush()
        return job_candidate

    async def shortlist_job_candidate(
        self,
        session: AsyncSession,
        job_candidate: JobCandidate,
        is_shortlisted: bool = True,
    ) -> JobCandidate:
        """Toggle is_shortlisted on job_candidate."""
        job_candidate.is_shortlisted = is_shortlisted
        await session.flush()
        return job_candidate

    async def reject_job_candidate(
        self,
        session: AsyncSession,
        job_candidate: JobCandidate,
        rejected_stage_id: uuid.UUID,
        rejection_reason: str | None = None,
    ) -> JobCandidate:
        """Move candidate to rejected stage and set rejection reason."""
        job_candidate.current_stage_id = rejected_stage_id
        job_candidate.rejection_reason = rejection_reason
        await session.flush()
        return job_candidate

    async def list_stage_history(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_candidate_id: uuid.UUID,
    ) -> list[CandidateStageHistory]:
        """Fetch timeline of stage transitions ordered by created_at ASC."""
        stmt = (
            select(CandidateStageHistory)
            .where(
                CandidateStageHistory.tenant_id == tenant_id,
                CandidateStageHistory.job_candidate_id == job_candidate_id,
            )
            .options(
                selectinload(CandidateStageHistory.from_stage),
                selectinload(CandidateStageHistory.to_stage),
                selectinload(CandidateStageHistory.actor),
            )
            .order_by(CandidateStageHistory.created_at.asc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_job_candidates_for_stage(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        job_id: uuid.UUID,
        stage_id: uuid.UUID,
    ) -> list[tuple[JobCandidate, Candidate, Score | None]]:
        """Fetch all candidates in a specific pipeline stage with score data for Kanban board."""
        stmt = (
            select(JobCandidate, Candidate, Score)
            .join(Candidate, JobCandidate.candidate_id == Candidate.id)
            .outerjoin(
                Score,
                (JobCandidate.id == Score.job_candidate_id) & (Score.is_current.is_(True)),
            )
            .where(
                JobCandidate.tenant_id == tenant_id,
                JobCandidate.job_id == job_id,
                JobCandidate.current_stage_id == stage_id,
            )
            .order_by(JobCandidate.created_at.desc())
        )
        result = await session.execute(stmt)
        return [(jc, cand, score) for jc, cand, score in result.all()]
