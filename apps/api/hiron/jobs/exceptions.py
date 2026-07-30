"""Custom domain exceptions for the Jobs module per API Contract §7."""

from hiron.common.exceptions import HironException


class JobNotFoundError(HironException):
    """Raised when a target job is not found within the tenant organization."""

    def __init__(self, message: str = "Job not found") -> None:
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=404,
        )


class InvalidJobDataError(HironException):
    """Raised when job input fields violate validation rules."""

    def __init__(self, message: str = "Invalid job data provided") -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
        )


class InvalidJobStatusTransitionError(HironException):
    """Raised when an illegal job status transition is attempted."""

    def __init__(self, message: str = "Invalid job status transition") -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=422,
        )


class InsufficientJobPermissionsError(HironException):
    """Raised when a user lacks required permissions for job operations."""

    def __init__(self, message: str = "Insufficient permissions for job operation") -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=403,
        )
