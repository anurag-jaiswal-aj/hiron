"""Note domain exceptions."""

from fastapi import status

from hiron.common.exceptions import HironException


class InsufficientNotePermissionsError(HironException):
    """Raised when user is not authorized to edit or delete a note."""

    def __init__(self, message: str = "Insufficient permissions for note operation") -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class NoteValidationError(HironException):
    """Raised when note content validation fails."""

    def __init__(
        self, message: str = "Note content must be between 1 and 5,000 characters"
    ) -> None:
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
