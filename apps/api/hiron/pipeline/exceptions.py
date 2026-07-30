"""Pipeline domain specific exceptions."""

from fastapi import status

from hiron.common.exceptions import HironException


class InsufficientPipelinePermissionsError(HironException):
    """Raised when user role is not authorized for candidate movement or stage modifications."""

    def __init__(self, message: str = "Insufficient permissions for pipeline operation") -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class PipelineStageValidationError(HironException):
    """Raised when stage transition validation fails per API Contract §PIPE-1."""

    def __init__(self, message: str = "Invalid pipeline stage transition") -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
