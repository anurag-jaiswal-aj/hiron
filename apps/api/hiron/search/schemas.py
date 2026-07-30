"""Pydantic schemas for Search domain per API Contract §CAND-7 and §SEARCH-1..4."""

import datetime
import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SearchCandidateFilters(BaseModel):
    """Optional metadata filters for candidate semantic search."""

    model_config = ConfigDict(populate_by_name=True)

    experience_min: int | None = Field(default=None, serialization_alias="experienceMin")
    experience_max: int | None = Field(default=None, serialization_alias="experienceMax")
    location: str | None = Field(default=None)
    skills: list[str] | None = Field(default=None)
    current_title: str | None = Field(default=None, serialization_alias="currentTitle")
    q: str | None = Field(default=None)


class SemanticSearchCandidatesRequest(BaseModel):
    """Request payload for candidate semantic search per API Contract §CAND-7."""

    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(..., min_length=3, max_length=500)
    filters: SearchCandidateFilters | None = Field(default=None)
    limit: int = Field(default=20, ge=1, le=100)


class CandidateSearchResultPayload(BaseModel):
    """Candidate details subset returned in semantic search result item."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    full_name: str = Field(..., serialization_alias="fullName")
    current_title: str | None = Field(default=None, serialization_alias="currentTitle")
    skills: list[str] = Field(default_factory=list)
    total_experience_years: int | None = Field(
        default=None, serialization_alias="totalExperienceYears"
    )


class CandidateSearchResultItem(BaseModel):
    """Single candidate match item with relevance score and highlights."""

    model_config = ConfigDict(populate_by_name=True)

    candidate: CandidateSearchResultPayload = Field(...)
    relevance_score: float = Field(..., serialization_alias="relevanceScore")
    highlights: list[str] = Field(default_factory=list)


class SearchPaginationData(BaseModel):
    """Pagination metadata for search results."""

    model_config = ConfigDict(populate_by_name=True)

    has_more: bool = Field(..., serialization_alias="hasMore")
    total_count: int = Field(..., serialization_alias="totalCount")


class SemanticSearchCandidatesResponse(BaseModel):
    """200 OK response for candidate semantic search per §CAND-7."""

    data: list[CandidateSearchResultItem] = Field(...)
    pagination: SearchPaginationData = Field(...)


class SavedSearchCreateRequest(BaseModel):
    """Request payload for creating a saved search per §SEARCH-2."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1, max_length=200)
    query_text: str = Field(..., validation_alias="queryText", serialization_alias="queryText")
    filters: dict[str, Any] = Field(default_factory=dict)
    is_shared: bool = Field(
        default=False, validation_alias="isShared", serialization_alias="isShared"
    )


class SavedSearchUpdateRequest(BaseModel):
    """Request payload for updating a saved search per §SEARCH-3."""

    model_config = ConfigDict(populate_by_name=True)

    name: str | None = Field(default=None, min_length=1, max_length=200)
    query_text: str | None = Field(
        default=None, validation_alias="queryText", serialization_alias="queryText"
    )
    filters: dict[str, Any] | None = Field(default=None)
    is_shared: bool | None = Field(
        default=None, validation_alias="isShared", serialization_alias="isShared"
    )


class SavedSearchData(BaseModel):
    """Detailed saved search model payload."""

    model_config = ConfigDict(populate_by_name=True)

    id: uuid.UUID = Field(...)
    tenant_id: uuid.UUID = Field(..., serialization_alias="tenantId")
    created_by: uuid.UUID = Field(..., serialization_alias="createdBy")
    name: str = Field(...)
    query_text: str = Field(..., serialization_alias="queryText")
    filters: dict[str, Any] = Field(...)
    is_shared: bool = Field(..., serialization_alias="isShared")
    created_at: datetime.datetime = Field(..., serialization_alias="createdAt")
    updated_at: datetime.datetime = Field(..., serialization_alias="updatedAt")


class SavedSearchResponse(BaseModel):
    """Single saved search response wrapper."""

    data: SavedSearchData = Field(...)


class SavedSearchListResponse(BaseModel):
    """List of saved searches response wrapper per §SEARCH-1."""

    data: list[SavedSearchData] = Field(...)
