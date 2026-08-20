"""Dashboard service aggregating metrics, pipeline overview progress, score distributions, and time-series analytics per API Contract."""

import datetime
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.dashboard.repository import DashboardRepository
from hiron.dashboard.schemas import (
    ActivityFeedItem,
    AnalyticsAggregationResponse,
    DashboardMetrics,
    DashboardSummaryData,
    DashboardSummaryResponse,
    JobPipelineOverview,
    JobStageOverview,
    ScoreDistributionData,
    TimeSeriesPoint,
)

logger = structlog.get_logger("hiron.dashboard.service")


class DashboardService:
    """Business service orchestrating recruitment dashboard aggregations and analytics data."""

    def __init__(self, dashboard_repository: DashboardRepository | None = None) -> None:
        self.dashboard_repo = dashboard_repository or DashboardRepository()

    async def get_dashboard_summary(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> DashboardSummaryResponse:
        """Fetch complete dashboard summary payload."""
        # 1. Metrics (Consolidated query for Phase 12 latency improvement)
        op, tot, sc, sh, hi = await self.dashboard_repo.get_dashboard_metrics_consolidated(
            session, tenant_id
        )
        metrics = DashboardMetrics(
            open_jobs_count=op,
            total_candidates_count=tot,
            scored_candidates_count=sc,
            shortlisted_candidates_count=sh,
            hired_candidates_count=hi,
        )

        # 2. Pipeline Overviews
        pipeline_overviews = await self.get_pipeline_overviews(session, tenant_id)

        # 3. Score Distribution
        score_dist = await self.get_score_distribution(session, tenant_id)

        # 4. Recent Activity
        activities = await self.dashboard_repo.get_recent_stage_activities(
            session, tenant_id, limit=10
        )
        feed_items: list[ActivityFeedItem] = []
        for a in activities:
            stage_name = a.to_stage.name if a.to_stage else "Stage"
            actor_name = a.actor.full_name if a.actor else "System"
            feed_items.append(
                ActivityFeedItem(
                    id=a.id,
                    activity_type="stage_change",
                    description=f"Moved candidate to stage '{stage_name}'",
                    actor_name=actor_name,
                    timestamp=a.created_at,
                )
            )

        logger.info("Retrieved dashboard summary sequentially", tenant_id=str(tenant_id))

        return DashboardSummaryResponse(
            data=DashboardSummaryData(
                metrics=metrics,
                pipeline_overview=pipeline_overviews,
                score_distribution=score_dist,
                recent_activity=feed_items,
            )
        )

    async def get_pipeline_overviews(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> list[JobPipelineOverview]:
        """Fetch pipeline stage candidate breakdowns for open jobs."""
        raw_overviews = await self.dashboard_repo.get_top_jobs_pipeline_overviews(
            session, tenant_id, limit=5
        )
        pipeline_overviews: list[JobPipelineOverview] = []

        for job, stage_tuples in raw_overviews:
            stage_overviews: list[JobStageOverview] = []
            job_total_candidates = 0
            for stage, count in stage_tuples:
                job_total_candidates += count
                stage_overviews.append(
                    JobStageOverview(
                        stage_id=stage.id,
                        stage_name=stage.name,
                        position=stage.position,
                        candidate_count=count,
                    )
                )

            pipeline_overviews.append(
                JobPipelineOverview(
                    job_id=job.id,
                    job_title=job.title,
                    status=job.status,
                    total_candidates=job_total_candidates,
                    stages=stage_overviews,
                )
            )

        return pipeline_overviews

    async def get_score_distribution(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> ScoreDistributionData:
        """Fetch AI candidate score distribution statistics."""
        high, medium, low, total, avg = await self.dashboard_repo.get_score_distribution_stats(
            session, tenant_id
        )
        return ScoreDistributionData(
            high_fit_count=high,
            medium_fit_count=medium,
            low_fit_count=low,
            total_scored=total,
            average_fit_score=avg,
        )

    async def get_analytics_aggregation(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        start_date: datetime.date | None = None,
        end_date: datetime.date | None = None,
    ) -> AnalyticsAggregationResponse:
        """Fetch time-series analytics for candidate applications and AI score evaluations."""
        today = datetime.datetime.now(datetime.UTC).date()
        effective_end = end_date or today
        effective_start = start_date or (effective_end - datetime.timedelta(days=30))

        app_counts = await self.dashboard_repo.get_application_counts_by_date(
            session, tenant_id, effective_start, effective_end
        )
        score_counts = await self.dashboard_repo.get_score_counts_by_date(
            session, tenant_id, effective_start, effective_end
        )

        points: list[TimeSeriesPoint] = []
        current_curr = effective_start
        while current_curr <= effective_end:
            points.append(
                TimeSeriesPoint(
                    date=current_curr,
                    applications_count=app_counts.get(current_curr, 0),
                    scores_count=score_counts.get(current_curr, 0),
                )
            )
            current_curr += datetime.timedelta(days=1)

        return AnalyticsAggregationResponse(data=points)
