"""Pydantic DTO schemas for Resume upload and status tracking per API Contract §RES-1..RES-4."""

import uuid
from datetime import datetime
from typing import Any

from pydantic import Field

from hiron.common.schemas import HironBaseModel


class UploadResumeResponse(HironBaseModel):
    """Response DTO for single resume upload per API Contract §RES-1."""

    resume_id: uuid.UUID
    candidate_id: uuid.UUID
    task_id: str
    status: str
    status_url: str


class BulkRejectionItem(HironBaseModel):
    """File rejection metadata item for bulk upload."""

    filename: str
    reason: str


class BulkUploadResumeResponse(HironBaseModel):
    """Response DTO for bulk resume upload per API Contract §RES-2."""

    task_id: str
    total_files: int
    accepted: int
    rejected: int
    rejections: list[BulkRejectionItem] = Field(default_factory=list)
    status_url: str


class ResumeStatusResponse(HironBaseModel):
    """Response DTO for resume parsing status per API Contract §RES-3."""

    resume_id: uuid.UUID
    status: str
    parse_confidence: float | None = None
    parsed_data: dict[str, Any] | None = None
    parse_error: str | None = None
    parser_model_version: str | None = None
    created_at: datetime
