"""Thin FastAPI router for Performance Optimization & Benchmarking per Phase 15."""

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.dependencies import get_current_user
from hiron.core.database import get_db_session as get_db
from hiron.performance.schemas import PerformanceReportResponse
from hiron.performance.service import PerformanceService
from hiron.users.models import User

router = APIRouter(tags=["Performance & Benchmarking"])


def get_performance_service() -> PerformanceService:
    """Dependency provider for PerformanceService."""
    return PerformanceService()


@router.get(
    "/performance/benchmark",
    response_model=PerformanceReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get System Performance & Latency Benchmarks (Phase 15)",
)
async def get_performance_benchmark_endpoint(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    service: PerformanceService = Depends(get_performance_service),
) -> PerformanceReportResponse:
    """Run live performance benchmarks and return query latency NFR compliance report."""
    return await service.run_performance_benchmarks(
        session=session,
        tenant_id=current_user.tenant_id,
    )
