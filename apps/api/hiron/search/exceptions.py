"""Search domain exceptions."""

from fastapi import status

from hiron.common.exceptions import HironException


class InsufficientSearchPermissionsError(HironException):
    """Raised when user role is not authorized for search operations."""

    def __init__(self, message: str = "Insufficient permissions for search operation") -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class SearchQueryValidationError(HironException):
    """Raised when search query violates validation rules per API Contract §CAND-7."""

    def __init__(self, message: str = "Search query must be between 3 and 500 characters") -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
