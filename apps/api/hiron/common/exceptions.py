"""Custom platform exceptions and global FastAPI exception handlers."""

from typing import Any, List, Optional

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

from hiron.common.schemas import ErrorBody, ErrorDetail, ErrorEnvelope

logger = structlog.get_logger("hiron.api.exceptions")


class HironException(Exception):
    """Base exception class for all Hiron platform errors."""

    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[List[ErrorDetail]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []


class ValidationException(HironException):
    """Raised when request payload fails validation rules."""

    def __init__(
        self,
        message: str = "Request validation failed",
        details: Optional[List[ErrorDetail]] = None,
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


class ResourceNotFoundException(HironException):
    """Raised when a requested entity does not exist or is in another tenant."""

    def __init__(self, message: str = "Requested resource not found") -> None:
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
        )


class ResourceConflictException(HironException):
    """Raised when creating or updating an entity violates uniqueness or state constraints."""

    def __init__(self, message: str = "Resource conflict detected") -> None:
        super().__init__(
            message=message,
            code="RESOURCE_CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
        )


class PermissionDeniedException(HironException):
    """Raised when an authenticated user lacks the required role or permission for an operation per API Contract §4."""

    def __init__(self, message: str = "Insufficient permissions for this action") -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class RateLimitExceededException(HironException):
    """Raised when a request exceeds the plan's rate limits."""

    def __init__(self, message: str = "Rate limit exceeded. Try again later.") -> None:
        super().__init__(
            message=message,
            code="RATE_LIMIT_EXCEEDED",
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        )


def register_exception_handlers(app: FastAPI) -> None:
    """Register custom exception handlers on the FastAPI application instance."""

    @app.exception_handler(HironException)
    async def hiron_exception_handler(request: Request, exc: HironException) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.warning(
            "Hiron business exception",
            code=exc.code,
            status_code=exc.status_code,
            message=exc.message,
        )
        payload = ErrorEnvelope(
            error=ErrorBody(
                code=exc.code,
                message=exc.message,
                details=exc.details if exc.details else None,
                request_id=request_id,
            )
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(by_alias=True, exclude_none=True),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        details: List[ErrorDetail] = []

        for err in exc.errors():
            loc = " -> ".join(str(item) for item in err.get("loc", []) if item != "body")
            details.append(
                ErrorDetail(
                    field=loc if loc else None,
                    message=err.get("msg", "Invalid value"),
                    value=str(err.get("input", "")) if err.get("input") is not None else None,
                )
            )

        logger.info("Request validation failed", details_count=len(details))
        payload = ErrorEnvelope(
            error=ErrorBody(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                details=details,
                request_id=request_id,
            )
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=payload.model_dump(by_alias=True, exclude_none=True),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        code_map: dict[int, str] = {
            401: "AUTHENTICATION_REQUIRED",
            403: "INSUFFICIENT_PERMISSIONS",
            404: "RESOURCE_NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            409: "RESOURCE_CONFLICT",
            429: "RATE_LIMIT_EXCEEDED",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        payload = ErrorEnvelope(
            error=ErrorBody(
                code=code,
                message=str(exc.detail),
                request_id=request_id,
            )
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=payload.model_dump(by_alias=True, exclude_none=True),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID")
        logger.error("Unhandled server exception", error=str(exc), exc_info=exc)
        payload = ErrorEnvelope(
            error=ErrorBody(
                code="INTERNAL_ERROR",
                message="An unexpected server error occurred.",
                request_id=request_id,
            )
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=payload.model_dump(by_alias=True, exclude_none=True),
        )
