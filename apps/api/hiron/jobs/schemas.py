"""Pydantic DTO request and response models for Jobs module per API Contract §7."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from hiron.common.schemas import HironBaseModel, PaginationMeta


class PipelineStageResponse(HironBaseModel):
    """Pipeline stage DTO payload representation."""

    id: uuid.UUID
    name: str
    position: int
    is_terminal: bool
    stage_type: str
    candidate_count: int = 0


class JobCreatorResponse(HironBaseModel):
    """Minimal creator details for job payload."""

    id: uuid.UUID
    full_name: str


class JobResponse(HironBaseModel):
    """Detailed job DTO payload per API Contract §JOB-2."""

    id: uuid.UUID
    title: str
    description: str
    department: str | None = None
    location: str | None = None
    employment_type: str | None = None
    experience_years_min: int | None = None
    experience_years_max: int | None = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    extracted_requirements: dict[str, Any] | None = None
    status: str
    is_archived: bool = False
    candidate_count: int = 0
    pipeline_stages: list[PipelineStageResponse] = Field(default_factory=list)
    created_by: JobCreatorResponse | None = None
    opened_at: datetime | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class JobListItemResponse(HironBaseModel):
    """Compact job item for list view per API Contract §JOB-1."""

    id: uuid.UUID
    title: str
    department: str | None = None
    location: str | None = None
    status: str
    employment_type: str | None = None
    candidate_count: int = 0
    opened_at: datetime | None = None
    created_at: datetime


class JobListResponse(HironBaseModel):
    """Paginated list envelope response for jobs."""

    data: list[JobListItemResponse]
    pagination: PaginationMeta


class JobCreateRequest(HironBaseModel):
    """Request body for creating a new job per API Contract §JOB-3."""

    title: str = Field(min_length=1, max_length=200, description="Job title")
    description: str = Field(min_length=1, max_length=10000, description="Full job description")
    department: str | None = Field(default=None, max_length=100, description="Department name")
    location: str | None = Field(default=None, max_length=200, description="Job location")
    employment_type: str | None = Field(
        default=None, description="Employment type (full_time, part_time, contract, internship)"
    )
    experience_years_min: int | None = Field(
        default=None, ge=0, le=50, description="Min years experience"
    )
    experience_years_max: int | None = Field(
        default=None, ge=0, le=50, description="Max years experience"
    )
    required_skills: list[str] = Field(
        default_factory=list, max_length=50, description="Required skills"
    )
    preferred_skills: list[str] = Field(
        default_factory=list, max_length=50, description="Preferred skills"
    )


class JobUpdateRequest(HironBaseModel):
    """Request body for partial job update per API Contract §JOB-4."""

    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1, max_length=10000)
    department: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    employment_type: str | None = Field(default=None)
    experience_years_min: int | None = Field(default=None, ge=0, le=50)
    experience_years_max: int | None = Field(default=None, ge=0, le=50)
    required_skills: list[str] | None = Field(default=None, max_length=50)
    preferred_skills: list[str] | None = Field(default=None, max_length=50)


class JobCloseRequest(HironBaseModel):
    """Optional request payload when closing a job per API Contract §JOB-7."""

    reason: str | None = Field(default=None, max_length=500)


class PipelineStageCreateRequest(HironBaseModel):
    """Request body for creating a custom pipeline stage."""

    name: str = Field(min_length=1, max_length=100, description="Stage display name")
    position: int | None = Field(
        default=None, ge=1, le=20, description="Optional 1-indexed sort position"
    )
    is_terminal: bool = Field(
        default=False, description="Whether this stage represents terminal outcome"
    )
    stage_type: str = Field(
        default="active", description="Stage type category (active, hired, rejected)"
    )


class PipelineStageUpdateRequest(HironBaseModel):
    """Request body for updating a pipeline stage."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    position: int | None = Field(default=None, ge=1, le=20)
    is_terminal: bool | None = Field(default=None)
    stage_type: str | None = Field(default=None)


class PipelineStageOrder(HironBaseModel):
    """Pairing of stage ID to target position for reordering."""

    stage_id: uuid.UUID
    position: int = Field(ge=1, le=20)


class PipelineStagesReorderRequest(HironBaseModel):
    """Request body for reordering job pipeline stages."""

    stages: list[PipelineStageOrder] = Field(min_length=1, max_length=20)
