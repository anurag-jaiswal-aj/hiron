"""AI Usage repository managing SQL persistence and cost/token aggregate calculations per Database Design §5.16."""

import datetime
import decimal
import uuid

from sqlalchemy import Integer, func, select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.ai_usage.models import AIUsageLog
from hiron.common.pagination import decode_cursor, encode_cursor


class AIUsageRepository:
    """Repository executing optimized aggregate queries on ai_usage_logs."""

    async def create_usage_log(
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
        """Insert and persist an AI usage record."""
        log = AIUsageLog(
            tenant_id=tenant_id,
            user_id=user_id,
            operation=operation,
            model_version=model_version,
            prompt_name=prompt_name,
            prompt_version=prompt_version,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            cost_usd=decimal.Decimal(str(cost_usd)),
            latency_ms=latency_ms,
            status=status,
            error_type=error_type,
            is_cache_hit=is_cache_hit,
        )
        session.add(log)
        await session.flush()
        return log

    async def get_summary_metrics(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
    ) -> tuple[float, int, int, float]:
        """Compute total cost USD, total tokens, total operations, and cache hit rate in date range."""
        stmt = select(
            func.coalesce(func.sum(AIUsageLog.cost_usd), 0),
            func.coalesce(func.sum(AIUsageLog.total_tokens), 0),
            func.count(AIUsageLog.id),
            func.coalesce(func.sum(func.cast(AIUsageLog.is_cache_hit, Integer())), 0),
        ).where(
            AIUsageLog.tenant_id == tenant_id,
            AIUsageLog.created_at >= start_dt,
            AIUsageLog.created_at <= end_dt,
        )
        result = await session.execute(stmt)
        cost_sum, token_sum, total_ops, cache_hits = result.one()

        cost_val = float(cost_sum)
        token_val = int(token_sum)
        ops_val = int(total_ops)
        cache_rate = (float(cache_hits) / ops_val) if ops_val > 0 else 0.0

        return round(cost_val, 2), token_val, ops_val, round(cache_rate, 4)

    async def get_operation_breakdown(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
    ) -> list[tuple[str, int, float, int]]:
        """Fetch per-operation count, sum(cost_usd), and avg(latency_ms)."""
        stmt = (
            select(
                AIUsageLog.operation,
                func.count(AIUsageLog.id),
                func.coalesce(func.sum(AIUsageLog.cost_usd), 0),
                func.coalesce(func.avg(AIUsageLog.latency_ms), 0),
            )
            .where(
                AIUsageLog.tenant_id == tenant_id,
                AIUsageLog.created_at >= start_dt,
                AIUsageLog.created_at <= end_dt,
            )
            .group_by(AIUsageLog.operation)
            .order_by(func.sum(AIUsageLog.cost_usd).desc())
        )
        result = await session.execute(stmt)
        return [(op, count, float(cost), int(avg_lat)) for op, count, cost, avg_lat in result.all()]

    async def get_daily_breakdown(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        start_dt: datetime.datetime,
        end_dt: datetime.datetime,
    ) -> list[tuple[str, float, int]]:
        """Fetch per-day cost USD and operation count."""
        stmt = (
            select(
                func.date(AIUsageLog.created_at),
                func.coalesce(func.sum(AIUsageLog.cost_usd), 0),
                func.count(AIUsageLog.id),
            )
            .where(
                AIUsageLog.tenant_id == tenant_id,
                AIUsageLog.created_at >= start_dt,
                AIUsageLog.created_at <= end_dt,
            )
            .group_by(func.date(AIUsageLog.created_at))
            .order_by(func.date(AIUsageLog.created_at).desc())
        )
        result = await session.execute(stmt)
        return [
            (str(dt), round(float(cost), 2), count)
            for dt, cost, count in result.all()
            if dt is not None
        ]

    async def list_usage_logs(
        self,
        session: AsyncSession,
        tenant_id: uuid.UUID,
        operation: str | None = None,
        status: str | None = None,
        start_dt: datetime.datetime | None = None,
        end_dt: datetime.datetime | None = None,
        limit: int = 20,
        cursor: str | None = None,
    ) -> tuple[list[AIUsageLog], bool, str | None]:
        """Fetch individual AI usage log records with filters and cursor pagination."""
        stmt = (
            select(AIUsageLog)
            .where(AIUsageLog.tenant_id == tenant_id)
            .order_by(AIUsageLog.created_at.desc(), AIUsageLog.id.desc())
        )

        if operation:
            stmt = stmt.where(AIUsageLog.operation == operation)
        if status:
            stmt = stmt.where(AIUsageLog.status == status)
        if start_dt:
            stmt = stmt.where(AIUsageLog.created_at >= start_dt)
        if end_dt:
            stmt = stmt.where(AIUsageLog.created_at <= end_dt)

        if cursor:
            decoded = decode_cursor(cursor)
            cursor_dt = datetime.datetime.fromisoformat(decoded["dt"])
            cursor_id = uuid.UUID(decoded["id"])

            stmt = stmt.where(
                tuple_(AIUsageLog.created_at, AIUsageLog.id) < tuple_(cursor_dt, cursor_id)
            )

        stmt = stmt.limit(limit + 1)
        result = await session.execute(stmt)
        rows = list(result.scalars().all())

        has_more = len(rows) > limit
        items = rows[:limit]

        next_cursor = None
        if has_more and items:
            last_item = items[-1]
            next_cursor = encode_cursor(
                {"dt": last_item.created_at.isoformat(), "id": str(last_item.id)}
            )

        return items, has_more, next_cursor
