"""Resume domain custom exception hierarchy per Engineering Guidelines §8 and API Contract §RES-1."""

from fastapi import status

from hiron.common.exceptions import (
    HironException,
    PermissionDeniedException,
    ResourceNotFoundException,
    ValidationException,
)


class ResumeNotFoundError(ResourceNotFoundException):
    """Raised when a requested resume entity cannot be found within the tenant context."""

    def __init__(self, message: str = "Resume not found") -> None:
        super().__init__(message=message)


class FileTooLargeError(HironException):
    """Raised when an uploaded resume file exceeds the 10 MB limit."""

    def __init__(self, message: str = "File size exceeds maximum allowed limit of 10 MB") -> None:
        super().__init__(
            message=message,
            code="FILE_TOO_LARGE",
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
        )


class UnsupportedFileTypeError(HironException):
    """Raised when an uploaded resume file is not an allowed type (PDF, DOCX, TXT)."""

    def __init__(
        self, message: str = "Unsupported file type. Only PDF, DOCX, and TXT files are allowed."
    ) -> None:
        super().__init__(
            message=message,
            code="UNSUPPORTED_FILE_TYPE",
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )


class ResumeParseFailedError(ValidationException):
    """Raised when resume parsing cannot be completed or retried."""

    def __init__(self, message: str = "Resume parse failed") -> None:
        super().__init__(message=message)


class InsufficientResumePermissionsError(PermissionDeniedException):
    """Raised when user role lacks permission to upload or manage resumes."""

    def __init__(
        self, message: str = "User lacks required permissions for resume operation"
    ) -> None:
        super().__init__(message=message)
