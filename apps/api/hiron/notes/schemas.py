"""Pydantic schemas for Candidate Notes per API Contract §NOTE-1..4."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class NoteAuthorInfo(BaseModel):
    """Author metadata embedded in note response."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    full_name: str = Field(..., serialization_alias="fullName")


class CreateNoteRequest(BaseModel):
    """Request payload for creating a note per API Contract §NOTE-2."""

    model_config = ConfigDict(populate_by_name=True)

    content: str = Field(..., min_length=1, max_length=5000)
    job_id: uuid.UUID | None = Field(default=None, alias="jobId", validation_alias="jobId")
    is_private: bool = Field(default=False, alias="isPrivate", validation_alias="isPrivate")


class UpdateNoteRequest(BaseModel):
    """Request payload for updating a note per API Contract §NOTE-3."""

    model_config = ConfigDict(populate_by_name=True)

    content: str | None = Field(default=None, min_length=1, max_length=5000)
    is_private: bool | None = Field(default=None, alias="isPrivate", validation_alias="isPrivate")


class NoteData(BaseModel):
    """Note model payload per API Contract §NOTE-1."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    candidate_id: uuid.UUID = Field(..., serialization_alias="candidateId")
    author: NoteAuthorInfo | None = Field(default=None)
    job_id: uuid.UUID | None = Field(default=None, serialization_alias="jobId")
    content: str = Field(...)
    is_private: bool = Field(..., serialization_alias="isPrivate")
    created_at: datetime.datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime.datetime = Field(..., serialization_alias="updatedAt")


class NoteResponse(BaseModel):
    """Single note response wrapper."""

    data: NoteData = Field(...)


class NoteListResponse(BaseModel):
    """List of candidate notes response wrapper per §NOTE-1."""

    data: list[NoteData] = Field(...)
