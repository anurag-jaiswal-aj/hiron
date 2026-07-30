"""Pydantic schemas for Embedding domain per API Contract §EMBED-1..EMBED-3."""

import uuid

from pydantic import BaseModel, ConfigDict, Field


class CandidateEmbeddingResponseData(BaseModel):
    """Data payload for candidate embedding generation response."""

    model_config = ConfigDict(populate_by_name=True)

    candidate_id: uuid.UUID = Field(..., alias="candidateId")
    task_id: str = Field(..., alias="taskId")
    status: str = Field(...)
    model_version: str = Field(..., alias="modelVersion")


class GenerateCandidateEmbeddingResponse(BaseModel):
    """202 Accepted response for candidate embedding generation per §EMBED-1."""

    data: CandidateEmbeddingResponseData = Field(...)


class JobEmbeddingResponseData(BaseModel):
    """Data payload for job embedding generation response."""

    model_config = ConfigDict(populate_by_name=True)

    job_id: uuid.UUID = Field(..., alias="jobId")
    task_id: str = Field(..., alias="taskId")
    status: str = Field(...)
    model_version: str = Field(..., alias="modelVersion")


class GenerateJobEmbeddingResponse(BaseModel):
    """202 Accepted response for job embedding generation per §EMBED-2."""

    data: JobEmbeddingResponseData = Field(...)


class CoverageMetricData(BaseModel):
    """Coverage stats for candidates or jobs."""

    model_config = ConfigDict(populate_by_name=True)

    total: int = Field(...)
    with_embedding: int = Field(..., alias="withEmbedding")
    stale: int = Field(...)
    missing: int = Field(...)
    model_version: str = Field(..., alias="modelVersion")


class EmbeddingStatusData(BaseModel):
    """Embedding status metric data."""

    candidates: CoverageMetricData = Field(...)
    jobs: CoverageMetricData = Field(...)


class EmbeddingStatusResponse(BaseModel):
    """200 OK response for tenant embedding status per §EMBED-3."""

    data: EmbeddingStatusData = Field(...)
