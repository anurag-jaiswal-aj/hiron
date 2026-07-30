"""Audit domain exceptions."""

from fastapi import status

from hiron.common.exceptions import HironException


class InsufficientAuditPermissionsError(HironException):
    """Raised when user role is not authorized for audit log access."""

    def __init__(self, message: str = "Insufficient permissions for audit log operation") -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class AuditLogValidationError(HironException):
    """Raised when audit query validation fails."""

    def __init__(self, message: str = "Invalid audit log query parameter") -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
