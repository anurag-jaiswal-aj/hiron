"""Dashboard repository performing SQL aggregation queries for recruitment analytics per Database Design."""

import datetime
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from hiron.candidates.models import Candidate, JobCandidate
from hiron.jobs.models import Job, PipelineStage
from hiron.pipeline.models import CandidateStageHistory
from hiron.scores.models import Score


class DashboardRepository:
    """Repository executing optimized database queries for dashboard metrics and analytics."""

    async def get_open_jobs_count(self, session: AsyncSession, tenant_id: uuid.UUID) -> int:
        """Count active open jobs for tenant."""
        stmt = select(func.count(Job.id)).where(
            Job.tenant_id == tenant_id,
            Job.status == "open",
            Job.is_archived.is_(False),
        )
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    async def get_total_candidates_count(self, session: AsyncSession, tenant_id: uuid.UUID) -> int:
        """Count total non-archived candidates for tenant."""
        stmt = select(func.count(Candidate.id)).where(
            Candidate.tenant_id == tenant_id,
            Candidate.is_archived.is_(False),
        )
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    async def get_scored_candidates_count(self, session: AsyncSession, tenant_id: uuid.UUID) -> int:
        """Count unique candidates with current AI fit scores."""
        stmt = select(func.count(func.distinct(Score.job_candidate_id))).where(
            Score.tenant_id == tenant_id,
            Score.is_current.is_(True),
        )
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    async def get_shortlisted_candidates_count(
        self, session: AsyncSession, tenant_id: uuid.UUID
    ) -> int:
        """Count job candidates currently shortlisted."""
        stmt = select(func.count(JobCandidate.id)).where(
            JobCandidate.tenant_id == tenant_id,
            JobCandidate.is_shortlisted.is_(True),
            JobCandidate.is_archived.is_(False),
        )
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    async def get_hired_candidates_count(self, session: AsyncSession, tenant_id: uuid.UUID) -> int:
        """Count job candidates in a 'Hired' pipeline stage."""
        stmt = (
            select(func.count(JobCandidate.id))
            .join(PipelineStage, JobCandidate.current_stage_id == PipelineStage.id)
            .where(
                JobCandidate.tenant_id == tenant_id,
                JobCandidate.is_archived.is_(False),
                func.lower(PipelineStage.name) == "hired",
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one() or 0

    async def get_top_jobs_pipeline_overviews(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        limit: int = 5,
    ) -> list[tuple[Job, list[tuple[PipelineStage, int]]]]:
        """Fetch top open jobs with stage candidate counts."""
        # 1. Fetch top jobs
        jobs_stmt = (
            select(Job)
            .where(
                Job.tenant_id == tenant_id,
                Job.status == "open",
                Job.is_archived.is_(False),
            )
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        jobs_res = await session.execute(jobs_stmt)
        jobs = list(jobs_res.scalars().all())

        if not jobs:
            return []

        job_ids = [j.id for j in jobs]

        # 2. Fetch stages and candidate counts for all top jobs in one query (Fixing N+1)
        stages_stmt = (
            select(PipelineStage, func.count(JobCandidate.id))
            .outerjoin(
                JobCandidate,
                (PipelineStage.id == JobCandidate.current_stage_id)
                & (JobCandidate.is_archived.is_(False)),
            )
            .where(
                PipelineStage.tenant_id == tenant_id,
                PipelineStage.job_id.in_(job_ids),
            )
            .group_by(PipelineStage.id)
            .order_by(PipelineStage.job_id, PipelineStage.position.asc())
        )
        stages_res = await session.execute(stages_stmt)
        all_stages = stages_res.all()

        # 3. Group stages by job_id in python
        stages_by_job: dict[uuid.UUID, list[tuple[PipelineStage, int]]] = {j.id: [] for j in jobs}
        for stage, count in all_stages:
            stages_by_job[stage.job_id].append((stage, count))

        results: list[tuple[Job, list[tuple[PipelineStage, int]]]] = []
        for j in jobs:
            results.append((j, stages_by_job[j.id]))

        return results

    async def get_score_distribution_stats(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> tuple[int, int, int, int, float | None]:
        """Compute high (>=80), medium (60-79), low (<60) score counts and average fit score."""
        from sqlalchemy import case, cast, Float
        scores_stmt = select(
            func.count(case((Score.fit_score >= 80, 1))).label("high"),
            func.count(case((Score.fit_score.between(60, 79), 1))).label("medium"),
            func.count(case((Score.fit_score < 60, 1))).label("low"),
            func.count(Score.id).label("total"),
            func.avg(Score.fit_score).label("avg"),
        ).where(
            Score.tenant_id == tenant_id,
            Score.is_current.is_(True),
        )
        res = await session.execute(scores_stmt)
        row = res.one()

        if row.total == 0:
            return 0, 0, 0, 0, None

        return row.high, row.medium, row.low, row.total, round(float(row.avg), 2)

    async def get_recent_stage_activities(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        limit: int = 10,
    ) -> list[CandidateStageHistory]:
        """Fetch recent candidate stage transition audit logs."""
        stmt = (
            select(CandidateStageHistory)
            .where(CandidateStageHistory.tenant_id == tenant_id)
            .options(
                selectinload(CandidateStageHistory.to_stage),
                selectinload(CandidateStageHistory.actor),
            )
            .order_by(CandidateStageHistory.created_at.desc())
            .limit(limit)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_application_counts_by_date(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> dict[datetime.date, int]:
        """Count candidate applications per date in date range."""
        start_dt = datetime.datetime.combine(start_date, datetime.time.min, tzinfo=datetime.UTC)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max, tzinfo=datetime.UTC)

        stmt = (
            select(func.date(JobCandidate.created_at), func.count(JobCandidate.id))
            .where(
                JobCandidate.tenant_id == tenant_id,
                JobCandidate.created_at >= start_dt,
                JobCandidate.created_at <= end_dt,
            )
            .group_by(func.date(JobCandidate.created_at))
        )
        res = await session.execute(stmt)
        return {d: count for d, count in res.all() if d is not None}

    async def get_score_counts_by_date(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime.date,
        end_date: datetime.date,
    ) -> dict[datetime.date, int]:
        """Count AI score evaluations per date in date range."""
        start_dt = datetime.datetime.combine(start_date, datetime.time.min, tzinfo=datetime.UTC)
        end_dt = datetime.datetime.combine(end_date, datetime.time.max, tzinfo=datetime.UTC)

        stmt = (
            select(func.date(Score.created_at), func.count(Score.id))
            .where(
                Score.tenant_id == tenant_id,
                Score.created_at >= start_dt,
                Score.created_at <= end_dt,
            )
            .group_by(func.date(Score.created_at))
        )
        res = await session.execute(stmt)
        return {d: count for d, count in res.all() if d is not None}
