"""Candidate domain custom exception hierarchy per Engineering Guidelines §8."""

from hiron.common.exceptions import (
    PermissionDeniedException,
    ResourceConflictException,
    ResourceNotFoundException,
    ValidationException,
)


class CandidateNotFoundError(ResourceNotFoundException):
    """Raised when candidate record cannot be found or does not belong to tenant."""

    def __init__(self, message: str = "Candidate not found") -> None:
        super().__init__(message=message)


class DuplicateCandidateEmailError(ResourceConflictException):
    """Raised when creating or updating candidate with an email that already exists within tenant."""

    def __init__(self, message: str = "Candidate email already exists in this tenant") -> None:
        super().__init__(message=message)


class InvalidCandidateDataError(ValidationException):
    """Raised when candidate input data violates domain business validation rules."""

    def __init__(self, message: str = "Invalid candidate data provided") -> None:
        super().__init__(message=message)


class InsufficientCandidatePermissionsError(PermissionDeniedException):
    """Raised when user role lacks permission to manage candidates."""

    def __init__(
        self, message: str = "User lacks required permissions for candidate operation"
    ) -> None:
        super().__init__(message=message)


class JobCandidateConflictError(ResourceConflictException):
    """Raised when candidate is already associated with the specified job."""

    def __init__(self, message: str = "Candidate is already associated with this job") -> None:
        super().__init__(message=message)
