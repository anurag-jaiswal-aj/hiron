"""Pydantic schemas and DTOs for Candidate Management per API Contract §CAND-1 through §CAND-6."""

import uuid
from datetime import datetime

from pydantic import EmailStr, Field

from hiron.common.schemas import HironBaseModel, PaginationMeta


class CandidateListItemResponse(HironBaseModel):
    """Candidate representation in list responses per API Contract §CAND-1."""

    id: uuid.UUID
    full_name: str
    email: str | None = None
    current_title: str | None = None
    current_company: str | None = None
    location: str | None = None
    total_experience_years: int | None = None
    skills: list[str] = Field(default_factory=list)
    source: str = "upload"
    is_archived: bool = False
    created_at: datetime


class CandidateAssociatedJobResponse(HironBaseModel):
    """Job association details for candidate detail response per API Contract §CAND-2."""

    job_id: uuid.UUID
    job_title: str
    current_stage: str
    is_shortlisted: bool = False


class CandidateResponse(HironBaseModel):
    """Full candidate profile details per API Contract §CAND-2."""

    id: uuid.UUID
    full_name: str
    email: str | None = None
    phone: str | None = None
    location: str | None = None
    linkedin_url: str | None = None
    summary: str | None = None
    skills: list[str] = Field(default_factory=list)
    total_experience_years: int | None = None
    current_title: str | None = None
    current_company: str | None = None
    source: str = "upload"
    is_archived: bool = False
    jobs: list[CandidateAssociatedJobResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class CandidateListResponse(HironBaseModel):
    """Paginated candidates array wrapper."""

    data: list[CandidateListItemResponse]
    pagination: PaginationMeta


class CandidateCreateRequest(HironBaseModel):
    """Request DTO for creating a candidate profile manually per API Contract §CAND-3."""

    full_name: str = Field(..., min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=200)
    linkedin_url: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None, max_length=5000)
    current_title: str | None = Field(default=None, max_length=200)
    current_company: str | None = Field(default=None, max_length=200)
    skills: list[str] = Field(default_factory=list)
    total_experience_years: int | None = Field(default=None, ge=0, le=70)
    source: str = Field(default="upload", max_length=50)


class CandidateUpdateRequest(HironBaseModel):
    """Request DTO for updating candidate profile fields per API Contract §CAND-4."""

    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    location: str | None = Field(default=None, max_length=200)
    linkedin_url: str | None = Field(default=None, max_length=500)
    summary: str | None = Field(default=None, max_length=5000)
    current_title: str | None = Field(default=None, max_length=200)
    current_company: str | None = Field(default=None, max_length=200)
    skills: list[str] | None = None
    total_experience_years: int | None = Field(default=None, ge=0, le=70)


class AddCandidateToJobRequest(HironBaseModel):
    """Request DTO for associating a candidate with a job per API Contract §CAND-6."""

    candidate_id: uuid.UUID


class StageSummaryResponse(HironBaseModel):
    """Summary of a pipeline stage in JobCandidate response."""

    id: uuid.UUID
    name: str
    position: int


class JobCandidateResponse(HironBaseModel):
    """Response DTO for candidate job association per API Contract §CAND-6."""

    id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    current_stage: StageSummaryResponse
    is_shortlisted: bool = False
    created_at: datetime
