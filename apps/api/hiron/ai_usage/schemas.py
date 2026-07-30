"""Pydantic schemas for AI Usage Monitoring per API Contract §USAGE-1..2."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class OperationUsageBreakdown(BaseModel):
    """Usage and cost statistics per operation type."""

    model_config = ConfigDict(populate_by_name=True)

    operation: str = Field(...)
    count: int = Field(...)
    cost_usd: float = Field(..., serialization_alias="costUsd")
    avg_latency_ms: int = Field(..., serialization_alias="avgLatencyMs")


class DailyUsagePoint(BaseModel):
    """Daily cost and operations point for trend chart."""

    model_config = ConfigDict(populate_by_name=True)

    date: str = Field(...)
    cost_usd: float = Field(..., serialization_alias="costUsd")
    operations: int = Field(...)


class AIUsageSummaryData(BaseModel):
    """Aggregated AI usage summary data payload per API Contract §USAGE-1."""

    model_config = ConfigDict(populate_by_name=True)

    total_cost_usd: float = Field(..., serialization_alias="totalCostUsd")
    total_tokens: int = Field(..., serialization_alias="totalTokens")
    total_operations: int = Field(..., serialization_alias="totalOperations")
    cache_hit_rate: float = Field(..., serialization_alias="cacheHitRate")
    by_operation: list[OperationUsageBreakdown] = Field(..., serialization_alias="byOperation")
    by_day: list[DailyUsagePoint] = Field(..., serialization_alias="byDay")


class AIUsageSummaryResponse(BaseModel):
    """Response wrapper for AI usage summary."""

    data: AIUsageSummaryData = Field(...)


class AIUsageLogItem(BaseModel):
    """Single AI usage log entry per API Contract §USAGE-2."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    operation: str = Field(...)
    model_version: str = Field(..., serialization_alias="modelVersion")
    prompt_name: str | None = Field(default=None, serialization_alias="promptName")
    input_tokens: int = Field(..., serialization_alias="inputTokens")
    output_tokens: int = Field(..., serialization_alias="outputTokens")
    total_tokens: int = Field(..., serialization_alias="totalTokens")
    cost_usd: float = Field(..., serialization_alias="costUsd")
    latency_ms: int = Field(..., serialization_alias="latencyMs")
    status: str = Field(...)
    is_cache_hit: bool = Field(..., serialization_alias="isCacheHit")
    created_at: datetime.datetime = Field(..., serialization_alias="createdAt")


class AIUsageLogPagination(BaseModel):
    """Pagination metadata for AI usage logs."""

    model_config = ConfigDict(populate_by_name=True)

    has_more: bool = Field(..., serialization_alias="hasMore")
    next_cursor: str | None = Field(default=None, serialization_alias="nextCursor")
    total_count: int | None = Field(default=None, serialization_alias="totalCount")


class AIUsageLogsResponse(BaseModel):
    """Response wrapper for AI usage log listing per §USAGE-2."""

    data: list[AIUsageLogItem] = Field(...)
    pagination: AIUsageLogPagination = Field(...)
