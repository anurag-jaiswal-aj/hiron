"""Pydantic schemas for Performance Optimization & Latency Benchmarks per Phase 15 requirements."""

from pydantic import BaseModel, ConfigDict, Field


class LatencyBenchmark(BaseModel):
    """Endpoint latency benchmark metric against NFR threshold."""

    model_config = ConfigDict(populate_by_name=True)

    target_name: str = Field(..., serialization_alias="targetName")
    latency_ms: float = Field(..., serialization_alias="latencyMs")
    threshold_ms: float = Field(..., serialization_alias="thresholdMs")
    status: str = Field(...)  # "PASSED" or "FAILED"


class CachePerformanceMetrics(BaseModel):
    """Cache efficiency and hit/miss statistics."""

    model_config = ConfigDict(populate_by_name=True)

    hits: int = Field(...)
    misses: int = Field(...)
    total_requests: int = Field(..., serialization_alias="totalRequests")
    hit_rate: float = Field(..., serialization_alias="hitRate")
    cached_entries_count: int = Field(..., serialization_alias="cachedEntriesCount")


class PerformanceReportData(BaseModel):
    """Complete performance benchmark and optimization report payload."""

    model_config = ConfigDict(populate_by_name=True)

    benchmarks: list[LatencyBenchmark] = Field(...)
    cache_stats: CachePerformanceMetrics = Field(..., serialization_alias="cacheStats")
    overall_status: str = Field(..., serialization_alias="overallStatus")


class PerformanceReportResponse(BaseModel):
    """Response wrapper for performance benchmark report."""

    data: PerformanceReportData = Field(...)
