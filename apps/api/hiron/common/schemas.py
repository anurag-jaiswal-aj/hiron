"""Standard API response envelopes, error structures, and base Pydantic model configurations."""

from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

T = TypeVar("T")


class HironBaseModel(BaseModel):
    """Base Pydantic model enforcing camelCase serialization for API JSON contracts."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class ResponseEnvelope(HironBaseModel, Generic[T]):
    """Standard success response wrapper envelope per API Contract §7."""

    data: T = Field(..., description="Response payload data")


class PaginationMeta(HironBaseModel):
    """Standard cursor pagination metadata per API Contract §9."""

    has_more: bool = Field(..., description="Whether additional pages exist")
    next_cursor: str | None = Field(
        default=None, description="Opaque cursor for fetching the next page"
    )
    total_count: int | None = Field(default=None, description="Total record count (if available)")


class PaginatedResponseEnvelope(HironBaseModel, Generic[T]):
    """Standard paginated success response wrapper envelope per API Contract §7 & §9."""

    data: list[T] = Field(..., description="Page items payload list")
    pagination: PaginationMeta = Field(..., description="Pagination metadata")


class ErrorDetail(HironBaseModel):
    """Individual field error detail item per API Contract §8."""

    field: str | None = Field(default=None, description="Field name experiencing validation error")
    message: str = Field(..., description="Human-readable error description")
    value: object | None = Field(default=None, description="Provided value that failed validation")


class ErrorBody(HironBaseModel):
    """Inner error detail structure per API Contract §8."""

    code: str = Field(..., description="Machine-readable error code string")
    message: str = Field(..., description="Human-readable error message")
    details: list[ErrorDetail] | None = Field(
        default=None, description="Per-field validation details"
    )
    request_id: str | None = Field(default=None, description="Unique trace request ID")


class ErrorEnvelope(HironBaseModel):
    """Standard error response envelope per API Contract §8."""

    error: ErrorBody = Field(..., description="Error body container")
