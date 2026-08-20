"""Pydantic schemas for Score domain per API Contract §SCORE-1..SCORE-5."""

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class BreakdownDimensionAI(BaseModel):
    score: int = Field(..., ge=0, le=100)
    details: str = Field(...)


class ScoreBreakdownAI(BaseModel):
    skills: BreakdownDimensionAI
    experience: BreakdownDimensionAI
    education: BreakdownDimensionAI


class AIGeneratedScore(BaseModel):
    fit_score: int = Field(..., ge=0, le=100, description="Overall fit score from 0 to 100")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the evaluation from 0.0 to 1.0"
    )
    explanation: str = Field(..., description="Overall summary explanation of candidate fit")
    skills_matched: list[str] = Field(
        ..., description="List of job required skills the candidate possesses"
    )
    skills_missing: list[str] = Field(
        ..., description="List of job required skills the candidate lacks"
    )
    breakdown: ScoreBreakdownAI


class BreakdownDimension(BaseModel):
    """Single scoring dimension score and explanation details."""

    score: int = Field(...)
    weight: float = Field(...)
    details: str = Field(...)


class ScoreBreakdown(BaseModel):
    """Dimensional breakdown for skills, experience, and education."""

    skills: BreakdownDimension = Field(...)
    experience: BreakdownDimension = Field(...)
    education: BreakdownDimension = Field(...)


class ScoreData(BaseModel):
    """Detailed score payload per API Contract §SCORE-1 & §SCORE-3."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    fit_score: int = Field(..., serialization_alias="fitScore")
    confidence: float = Field(...)
    breakdown: dict[str, Any] = Field(...)
    explanation: str = Field(...)
    skills_matched: list[str] = Field(..., serialization_alias="skillsMatched")
    skills_missing: list[str] = Field(..., serialization_alias="skillsMissing")
    warnings: list[str] = Field(default_factory=list)
    prompt_version: str = Field(..., serialization_alias="promptVersion")
    model_version: str = Field(..., serialization_alias="modelVersion")
    is_current: bool = Field(..., serialization_alias="isCurrent")
    created_at: datetime.datetime = Field(..., serialization_alias="createdAt")


class ScoreResponse(BaseModel):
    """200 OK response for candidate-job scoring per §SCORE-1 & §SCORE-3."""

    data: ScoreData = Field(...)


class BatchScoreRequest(BaseModel):
    """Request payload for batch scoring per API Contract §SCORE-2."""

    model_config = ConfigDict(populate_by_name=True)

    candidate_ids: list[uuid.UUID] | None = Field(default=None, alias="candidateIds")
    force_rescore: bool = Field(default=False, alias="forceRescore")


class BatchScoreData(BaseModel):
    """Data payload for batch score response."""

    model_config = ConfigDict(populate_by_name=True)

    task_id: str = Field(..., serialization_alias="taskId")
    candidates_queued: int = Field(..., serialization_alias="candidatesQueued")
    estimated_completion_seconds: int = Field(..., serialization_alias="estimatedCompletionSeconds")
    status_url: str = Field(..., serialization_alias="statusUrl")


class BatchScoreResponse(BaseModel):
    """202 Accepted response for batch candidate scoring per §SCORE-2."""

    data: BatchScoreData = Field(...)


class ScoreHistoryItem(BaseModel):
    """Item in score history list per API Contract §SCORE-4."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    fit_score: int = Field(..., serialization_alias="fitScore")
    prompt_version: str = Field(..., serialization_alias="promptVersion")
    is_current: bool = Field(..., serialization_alias="isCurrent")
    created_at: datetime.datetime = Field(..., serialization_alias="createdAt")


class ScoreHistoryResponse(BaseModel):
    """200 OK response for score history list per §SCORE-4."""

    data: list[ScoreHistoryItem] = Field(...)


class ConfidenceFactorsData(BaseModel):
    """Confidence evaluation factors breakdown."""

    model_config = ConfigDict(populate_by_name=True)

    resume_completeness: float = Field(..., serialization_alias="resumeCompleteness")
    output_consistency: float = Field(..., serialization_alias="outputConsistency")
    explanation_quality: float = Field(..., serialization_alias="explanationQuality")
    sanity_check_passed: bool = Field(..., serialization_alias="sanityCheckPassed")


class ScoreExplanationData(BaseModel):
    """Detailed score explanation payload per API Contract §SCORE-5."""

    model_config = ConfigDict(populate_by_name=True)

    score_id: uuid.UUID = Field(..., serialization_alias="scoreId")
    fit_score: int = Field(..., serialization_alias="fitScore")
    explanation: str = Field(...)
    breakdown: dict[str, Any] = Field(...)
    skills_matched: list[str] = Field(..., serialization_alias="skillsMatched")
    skills_missing: list[str] = Field(..., serialization_alias="skillsMissing")
    warnings: list[str] = Field(...)
    confidence: float = Field(...)
    confidence_factors: ConfidenceFactorsData = Field(..., serialization_alias="confidenceFactors")


class ScoreExplanationResponse(BaseModel):
    """200 OK response for score explanation per §SCORE-5."""

    data: ScoreExplanationData = Field(...)


class BatchScoreWorkerWebhookPayload(BaseModel):
    batch_id: str
    tenant_id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    force_rescore: bool


class BatchScoreCoordinatorWebhookPayload(BaseModel):
    batch_id: str
    tenant_id: uuid.UUID
    job_id: uuid.UUID
    candidate_ids: list[uuid.UUID]
    force_rescore: bool
