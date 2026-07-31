"""Pydantic DTO request and response models for Maintenance & Post-Launch Subsystem."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field

from hiron.common.schemas import HironBaseModel


class SubsystemStatusInfo(BaseModel):
    """Subsystem status details."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(...)
    status: str = Field(...)
    details: str = Field(...)


class MaintenanceStatusData(BaseModel):
    """Complete post-launch maintenance status data payload."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="operational", description="System operational status")
    environment: str = Field(..., description="Active deployment environment")
    subsystems: list[SubsystemStatusInfo] = Field(default_factory=list)
    timestamp: datetime.datetime = Field(...)


class MaintenanceStatusResponse(HironBaseModel):
    """Envelope response for maintenance status endpoint."""

    data: MaintenanceStatusData = Field(...)


class MaintenanceCleanupRequest(BaseModel):
    """Request payload for triggerable maintenance cleanup operations."""

    model_config = ConfigDict(populate_by_name=True)

    purge_expired_tokens: bool = Field(default=True, description="Purge expired refresh tokens")
    purge_archived_notes: bool = Field(
        default=False, description="Purge soft-deleted candidate notes older than 90 days"
    )
    vacuum_analyze: bool = Field(
        default=False, description="Trigger database table statistics refresh"
    )


class MaintenanceCleanupData(BaseModel):
    """Result data for maintenance cleanup operation."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: uuid.UUID = Field(..., serialization_alias="jobId")
    expired_tokens_purged: int = Field(..., serialization_alias="expiredTokensPurged")
    archived_notes_purged: int = Field(..., serialization_alias="archivedNotesPurged")
    cache_cleared: bool = Field(..., serialization_alias="cacheCleared")
    executed_at: datetime.datetime = Field(..., serialization_alias="executedAt")


class MaintenanceCleanupResponse(HironBaseModel):
    """Envelope response for cleanup endpoint."""

    data: MaintenanceCleanupData = Field(...)


class CachePurgeData(BaseModel):
    """Cache purge operation result."""

    model_config = ConfigDict(populate_by_name=True)

    status: str = Field(default="purged")
    hit_count_reset: bool = Field(..., serialization_alias="hitCountReset")
    purged_at: datetime.datetime = Field(..., serialization_alias="purgedAt")


class CachePurgeResponse(HironBaseModel):
    """Envelope response for cache purge endpoint."""

    data: CachePurgeData = Field(...)


class AIQualityMetricsData(BaseModel):
    """AI model performance and scoring quality metrics payload."""

    model_config = ConfigDict(populate_by_name=True)

    average_confidence: float = Field(..., serialization_alias="averageConfidence")
    score_variance: float = Field(..., serialization_alias="scoreVariance")
    total_evaluations_analyzed: int = Field(..., serialization_alias="totalEvaluationsAnalyzed")
    high_confidence_ratio: float = Field(..., serialization_alias="highConfidenceRatio")
    model_version: str = Field(..., serialization_alias="modelVersion")
    analyzed_at: datetime.datetime = Field(..., serialization_alias="analyzedAt")


class AIQualityMetricsResponse(HironBaseModel):
    """Envelope response for AI quality metrics endpoint."""

    data: AIQualityMetricsData = Field(...)
