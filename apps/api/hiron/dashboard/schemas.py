"""Pydantic schemas for Dashboard & Analytics domain per API Contract and IMPLEMENTATION_ROADMAP.md Phase 12."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class DashboardMetrics(BaseModel):
    """Core metric cards overview."""

    model_config = ConfigDict(populate_by_name=True)

    open_jobs_count: int = Field(..., serialization_alias="openJobsCount")
    total_candidates_count: int = Field(..., serialization_alias="totalCandidatesCount")
    scored_candidates_count: int = Field(..., serialization_alias="scoredCandidatesCount")
    shortlisted_candidates_count: int = Field(..., serialization_alias="shortlistedCandidatesCount")
    hired_candidates_count: int = Field(..., serialization_alias="hiredCandidatesCount")


class JobStageOverview(BaseModel):
    """Pipeline stage candidate count breakdown for a job."""

    model_config = ConfigDict(populate_by_name=True)

    stage_id: uuid.UUID = Field(..., serialization_alias="stageId")
    stage_name: str = Field(..., serialization_alias="stageName")
    position: int = Field(...)
    candidate_count: int = Field(..., serialization_alias="candidateCount")


class JobPipelineOverview(BaseModel):
    """Job pipeline summary with mini stage breakdowns."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: uuid.UUID = Field(..., serialization_alias="jobId")
    job_title: str = Field(..., serialization_alias="jobTitle")
    status: str = Field(...)
    total_candidates: int = Field(..., serialization_alias="totalCandidates")
    stages: list[JobStageOverview] = Field(default_factory=list)


class ScoreDistributionData(BaseModel):
    """AI fit score breakdown statistics."""

    model_config = ConfigDict(populate_by_name=True)

    high_fit_count: int = Field(..., serialization_alias="highFitCount")  # score >= 80
    medium_fit_count: int = Field(..., serialization_alias="mediumFitCount")  # 60 <= score < 80
    low_fit_count: int = Field(..., serialization_alias="lowFitCount")  # score < 60
    total_scored: int = Field(..., serialization_alias="totalScored")
    average_fit_score: float | None = Field(default=None, serialization_alias="averageFitScore")


class ActivityFeedItem(BaseModel):
    """Recent activity log entry for dashboard feed."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    activity_type: str = Field(..., serialization_alias="activityType")
    description: str = Field(...)
    actor_name: str | None = Field(default=None, serialization_alias="actorName")
    timestamp: datetime.datetime = Field(...)


class DashboardSummaryData(BaseModel):
    """Complete dashboard summary payload."""

    model_config = ConfigDict(populate_by_name=True)

    metrics: DashboardMetrics = Field(...)
    pipeline_overview: list[JobPipelineOverview] = Field(
        ..., serialization_alias="pipelineOverview"
    )
    score_distribution: ScoreDistributionData = Field(..., serialization_alias="scoreDistribution")
    recent_activity: list[ActivityFeedItem] = Field(..., serialization_alias="recentActivity")


class DashboardSummaryResponse(BaseModel):
    """Dashboard summary response wrapper."""

    data: DashboardSummaryData = Field(...)


class TimeSeriesPoint(BaseModel):
    """Time-series analytics aggregation data point."""

    model_config = ConfigDict(populate_by_name=True)

    date: datetime.date = Field(...)
    applications_count: int = Field(..., serialization_alias="applicationsCount")
    scores_count: int = Field(..., serialization_alias="scoresCount")


class AnalyticsAggregationResponse(BaseModel):
    """Analytics aggregation response wrapper."""

    data: list[TimeSeriesPoint] = Field(...)
