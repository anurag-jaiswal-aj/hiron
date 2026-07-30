"""Performance benchmarking service executing live latency timing checks against NFR target thresholds."""

import time
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.core.cache import app_cache
from hiron.dashboard.repository import DashboardRepository
from hiron.performance.schemas import (
    CachePerformanceMetrics,
    LatencyBenchmark,
    PerformanceReportData,
    PerformanceReportResponse,
)

logger = structlog.get_logger("hiron.performance.service")


class PerformanceService:
    """Service evaluating database query performance and cache metrics against target NFR thresholds."""

    def __init__(
        self,
        dashboard_repository: DashboardRepository | None = None,
    ) -> None:
        self.dashboard_repo = dashboard_repository or DashboardRepository()

    async def run_performance_benchmarks(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
    ) -> PerformanceReportResponse:
        """Benchmark core query pathways and verify NFR latency target compliance."""
        benchmarks: list[LatencyBenchmark] = []

        # 1. Dashboard Summary Benchmark (Target: < 500ms)
        t0 = time.monotonic()
        await self.dashboard_repo.get_open_jobs_count(session, tenant_id)
        await self.dashboard_repo.get_total_candidates_count(session, tenant_id)
        await self.dashboard_repo.get_scored_candidates_count(session, tenant_id)
        await self.dashboard_repo.get_shortlisted_candidates_count(session, tenant_id)
        t1 = time.monotonic()
        dash_latency = round((t1 - t0) * 1000, 2)
        benchmarks.append(
            LatencyBenchmark(
                target_name="Dashboard Summary Aggregations",
                latency_ms=dash_latency,
                threshold_ms=500.0,
                status="PASSED" if dash_latency <= 500.0 else "FAILED",
            )
        )

        # 2. Top Pipeline Overview Benchmark (Target: < 1000ms)
        t0 = time.monotonic()
        await self.dashboard_repo.get_top_jobs_pipeline_overviews(session, tenant_id, limit=5)
        t1 = time.monotonic()
        pipeline_latency = round((t1 - t0) * 1000, 2)
        benchmarks.append(
            LatencyBenchmark(
                target_name="Pipeline Kanban Board Query",
                latency_ms=pipeline_latency,
                threshold_ms=1000.0,
                status="PASSED" if pipeline_latency <= 1000.0 else "FAILED",
            )
        )

        # 3. AI Score Distribution Benchmark (Target: < 300ms)
        t0 = time.monotonic()
        await self.dashboard_repo.get_score_distribution_stats(session, tenant_id)
        t1 = time.monotonic()
        score_latency = round((t1 - t0) * 1000, 2)
        benchmarks.append(
            LatencyBenchmark(
                target_name="AI Score Distribution Query",
                latency_ms=score_latency,
                threshold_ms=300.0,
                status="PASSED" if score_latency <= 300.0 else "FAILED",
            )
        )

        # 4. Cache statistics
        stats = app_cache.get_stats()
        cache_metrics = CachePerformanceMetrics(
            hits=stats["hits"],
            misses=stats["misses"],
            total_requests=stats["total_requests"],
            hit_rate=stats["hit_rate"],
            cached_entries_count=stats["cached_entries_count"],
        )

        overall_status = "PASSED" if all(b.status == "PASSED" for b in benchmarks) else "WARNING"

        logger.info(
            "Executed performance benchmarks",
            tenant_id=str(tenant_id),
            overall_status=overall_status,
            benchmarks_count=len(benchmarks),
        )

        return PerformanceReportResponse(
            data=PerformanceReportData(
                benchmarks=benchmarks,
                cache_stats=cache_metrics,
                overall_status=overall_status,
            )
        )
