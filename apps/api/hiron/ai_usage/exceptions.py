"""AI Usage domain exceptions."""

from fastapi import status

from hiron.common.exceptions import HironException


class InsufficientAIUsagePermissionsError(HironException):
    """Raised when user role is not authorized for AI usage analytics."""

    def __init__(self, message: str = "Only org_admin users can access AI usage analytics") -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class AIUsageValidationError(HironException):
    """Raised when usage parameters or period values are invalid."""

    def __init__(self, message: str = "Invalid AI usage query parameter") -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
