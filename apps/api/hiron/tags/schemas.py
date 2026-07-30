"""Pydantic schemas for Candidate Tags per API Contract §TAG-1..3."""

import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class TagUserPayload(BaseModel):
    """User who applied tag."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    full_name: str = Field(..., serialization_alias="fullName")


class AddTagRequest(BaseModel):
    """Request payload for adding a tag to candidate per API Contract §TAG-2."""

    model_config = ConfigDict(populate_by_name=True)

    tag_name: str = Field(
        ..., min_length=1, max_length=50, alias="tagName", validation_alias="tagName"
    )


class TagData(BaseModel):
    """Tag payload per API Contract §TAG-1."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    tag_name: str = Field(..., serialization_alias="tagName")
    tagged_by: TagUserPayload | None = Field(default=None, serialization_alias="taggedBy")
    created_at: datetime.datetime = Field(..., serialization_alias="createdAt")


class TagResponse(BaseModel):
    """Single tag response wrapper."""

    data: TagData = Field(...)


class TagListResponse(BaseModel):
    """List of candidate tags response wrapper per §TAG-1."""

    data: list[TagData] = Field(...)
