"""AI Usage service managing org_admin RBAC security, time-window aggregations, and log queries per API Contract §USAGE-1..2."""

import datetime
import decimal
import uuid

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.ai_usage.exceptions import (
    AIUsageValidationError,
    InsufficientAIUsagePermissionsError,
)
from hiron.ai_usage.models import AIUsageLog
from hiron.ai_usage.repository import AIUsageRepository
from hiron.ai_usage.schemas import (
    AIUsageLogItem,
    AIUsageLogPagination,
    AIUsageLogsResponse,
    AIUsageSummaryData,
    AIUsageSummaryResponse,
    DailyUsagePoint,
    OperationUsageBreakdown,
)

logger = structlog.get_logger("hiron.ai_usage.service")


class AIUsageService:
    """Business service handling AI cost/token analytics and org_admin authorization."""

    def __init__(self, ai_usage_repository: AIUsageRepository | None = None) -> None:
        self.usage_repo = ai_usage_repository or AIUsageRepository()

    def _validate_admin_permissions(self, role: str) -> None:
        """Validate that user role is org_admin (strict access control for AI usage analytics)."""
        if role != "org_admin":
            raise InsufficientAIUsagePermissionsError(
                f"User with role '{role}' is not authorized to access AI usage analytics"
            )

    def _build_log_item(self, log: AIUsageLog) -> AIUsageLogItem:
        """Convert AIUsageLog ORM model to Pydantic AIUsageLogItem schema."""
        return AIUsageLogItem(
            id=log.id,
            operation=log.operation,
            model_version=log.model_version,
            prompt_name=log.prompt_name,
            input_tokens=log.input_tokens,
            output_tokens=log.output_tokens,
            total_tokens=log.total_tokens,
            cost_usd=float(log.cost_usd),
            latency_ms=log.latency_ms,
            status=log.status,
            is_cache_hit=log.is_cache_hit,
            created_at=log.created_at,
        )

    async def get_usage_summary(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        period: str = "30d",
        group_by: str = "day",
    ) -> AIUsageSummaryResponse:
        """Get aggregated AI usage and cost summary for tenant per API Contract §USAGE-1."""
        self._validate_admin_permissions(user_role)

        if period not in ("7d", "30d", "90d"):
            raise AIUsageValidationError(
                f"Invalid period parameter '{period}'. Must be 7d, 30d, or 90d"
            )

        days_map = {"7d": 7, "30d": 30, "90d": 90}
        days = days_map[period]

        now = datetime.datetime.now(datetime.UTC)
        start_dt = now - datetime.timedelta(days=days)

        total_cost, total_tokens, total_ops, cache_rate = await self.usage_repo.get_summary_metrics(
            session=session, tenant_id=tenant_id, start_dt=start_dt, end_dt=now
        )

        ops_breakdown_raw = await self.usage_repo.get_operation_breakdown(
            session=session, tenant_id=tenant_id, start_dt=start_dt, end_dt=now
        )
        ops_breakdown = [
            OperationUsageBreakdown(
                operation=op,
                count=cnt,
                cost_usd=round(cost, 4),
                avg_latency_ms=lat,
            )
            for op, cnt, cost, lat in ops_breakdown_raw
        ]

        daily_breakdown_raw = await self.usage_repo.get_daily_breakdown(
            session=session, tenant_id=tenant_id, start_dt=start_dt, end_dt=now
        )
        daily_points = [
            DailyUsagePoint(date=dt_str, cost_usd=cost, operations=cnt)
            for dt_str, cost, cnt in daily_breakdown_raw
        ]

        logger.info(
            "Retrieved AI usage summary",
            tenant_id=str(tenant_id),
            period=period,
            group_by=group_by,
            total_cost_usd=total_cost,
        )

        return AIUsageSummaryResponse(
            data=AIUsageSummaryData(
                total_cost_usd=total_cost,
                total_tokens=total_tokens,
                total_operations=total_ops,
                cache_hit_rate=cache_rate,
                by_operation=ops_breakdown,
                by_day=daily_points,
            )
        )

    async def list_usage_logs(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        user_role: str,
        operation: str | None = None,
        status: str | None = None,
        start_date: datetime.datetime | None = None,
        end_date: datetime.datetime | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> AIUsageLogsResponse:
        """List individual AI operation records per API Contract §USAGE-2."""
        self._validate_admin_permissions(user_role)

        items, has_more, next_cursor = await self.usage_repo.list_usage_logs(
            session=session,
            tenant_id=tenant_id,
            operation=operation,
            status=status,
            start_dt=start_date,
            end_dt=end_date,
            limit=limit,
            cursor=cursor,
        )

        return AIUsageLogsResponse(
            data=[self._build_log_item(log) for log in items],
            pagination=AIUsageLogPagination(
                has_more=has_more,
                next_cursor=next_cursor,
                total_count=None,
            ),
        )

    async def record_ai_usage(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        operation: str,
        model_version: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float | decimal.Decimal,
        latency_ms: int,
        user_id: uuid.UUID | None = None,
        prompt_name: str | None = None,
        prompt_version: str | None = None,
        status: str = "success",
        error_type: str | None = None,
        is_cache_hit: bool = False,
    ) -> AIUsageLog:
        """Helper to create and persist an AI usage log entry."""
        return await self.usage_repo.create_usage_log(
            session=session,
            tenant_id=tenant_id,
            user_id=user_id,
            operation=operation,
            model_version=model_version,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            latency_ms=latency_ms,
            status=status,
            error_type=error_type,
            is_cache_hit=is_cache_hit,
        )
