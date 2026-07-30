"""Pydantic schemas for Pipeline domain per API Contract §PIPE-1..4."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class StageInfo(BaseModel):
    """Pipeline stage metadata subset."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    name: str = Field(...)
    position: int = Field(...)


class UserInfo(BaseModel):
    """User actor metadata subset."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    full_name: str = Field(..., serialization_alias="fullName")


class MoveCandidateStageRequest(BaseModel):
    """Request payload for candidate stage movement per API Contract §PIPE-1."""

    model_config = ConfigDict(populate_by_name=True)

    job_candidate_id: uuid.UUID = Field(
        ..., alias="jobCandidateId", validation_alias="jobCandidateId"
    )
    to_stage_id: uuid.UUID = Field(..., alias="toStageId", validation_alias="toStageId")
    note: str | None = Field(default=None, max_length=2000)


class MoveCandidateStageData(BaseModel):
    """Result data for stage transition per §PIPE-1."""

    model_config = ConfigDict(populate_by_name=True)

    job_candidate_id: uuid.UUID = Field(..., serialization_alias="jobCandidateId")
    previous_stage: StageInfo | None = Field(default=None, serialization_alias="previousStage")
    current_stage: StageInfo = Field(..., serialization_alias="currentStage")
    moved_by: UserInfo | None = Field(default=None, serialization_alias="movedBy")
    note: str | None = Field(default=None)
    moved_at: datetime.datetime = Field(..., serialization_alias="movedAt")


class MoveCandidateStageResponse(BaseModel):
    """200 OK response for candidate stage movement per §PIPE-1."""

    data: MoveCandidateStageData = Field(...)


class StageHistoryItem(BaseModel):
    """Timeline entry for stage transition per API Contract §PIPE-2."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    from_stage: StageInfo | None = Field(default=None, serialization_alias="fromStage")
    to_stage: StageInfo = Field(..., serialization_alias="toStage")
    moved_by: UserInfo | None = Field(default=None, serialization_alias="movedBy")
    note: str | None = Field(default=None)
    created_at: datetime.datetime = Field(..., serialization_alias="createdAt")


class StageHistoryResponse(BaseModel):
    """200 OK response for stage transition history per §PIPE-2."""

    data: list[StageHistoryItem] = Field(...)


class ShortlistCandidateData(BaseModel):
    """Result data for candidate shortlisting per §PIPE-3."""

    model_config = ConfigDict(populate_by_name=True)

    job_candidate_id: uuid.UUID = Field(..., serialization_alias="jobCandidateId")
    is_shortlisted: bool = Field(..., serialization_alias="isShortlisted")
    shortlisted_at: datetime.datetime = Field(..., serialization_alias="shortlistedAt")


class ShortlistCandidateResponse(BaseModel):
    """200 OK response for shortlisting candidate per §PIPE-3."""

    data: ShortlistCandidateData = Field(...)


class RejectCandidateRequest(BaseModel):
    """Request payload for rejecting candidate per API Contract §PIPE-4."""

    model_config = ConfigDict(populate_by_name=True)

    reason: str | None = Field(default=None, max_length=500)


class RejectCandidateData(BaseModel):
    """Result data for rejecting candidate per §PIPE-4."""

    model_config = ConfigDict(populate_by_name=True)

    job_candidate_id: uuid.UUID = Field(..., serialization_alias="jobCandidateId")
    status: str = Field(...)
    rejection_reason: str | None = Field(default=None, serialization_alias="rejectionReason")
    rejected_at: datetime.datetime = Field(..., serialization_alias="rejectedAt")


class RejectCandidateResponse(BaseModel):
    """200 OK response for candidate rejection per §PIPE-4."""

    data: RejectCandidateData = Field(...)


class KanbanCandidateCard(BaseModel):
    """Candidate card payload displayed in Kanban board columns."""

    model_config = ConfigDict(populate_by_name=True)

    candidate_id: uuid.UUID = Field(..., serialization_alias="candidateId")
    job_candidate_id: uuid.UUID = Field(..., serialization_alias="jobCandidateId")
    full_name: str = Field(..., serialization_alias="fullName")
    current_title: str | None = Field(default=None, serialization_alias="currentTitle")
    fit_score: int | None = Field(default=None, serialization_alias="fitScore")
    confidence: float | None = Field(default=None)
    is_shortlisted: bool = Field(..., serialization_alias="isShortlisted")
    applied_at: datetime.datetime = Field(..., serialization_alias="appliedAt")


class PipelineStageStats(BaseModel):
    """Stage column metadata and candidate cards for Kanban board."""

    model_config = ConfigDict(populate_by_name=True)

    stage_id: uuid.UUID = Field(..., serialization_alias="stageId")
    stage_name: str = Field(..., serialization_alias="stageName")
    position: int = Field(...)
    candidate_count: int = Field(..., serialization_alias="candidateCount")
    candidates: list[KanbanCandidateCard] = Field(default_factory=list)


class PipelineBoardResponse(BaseModel):
    """Kanban pipeline board response wrapper."""

    data: list[PipelineStageStats] = Field(...)
