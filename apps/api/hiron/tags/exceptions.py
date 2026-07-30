"""Tag domain exceptions."""

from fastapi import status

from hiron.common.exceptions import HironException


class InsufficientTagPermissionsError(HironException):
    """Raised when user role is not authorized for tag operations."""

    def __init__(self, message: str = "Insufficient permissions for tag operation") -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class DuplicateTagError(HironException):
    """Raised when tag already exists on candidate per API Contract §TAG-2 (HTTP 409 Conflict)."""

    def __init__(self, message: str = "Tag already exists on this candidate") -> None:
        super().__init__(
            message=message,
            code="RESOURCE_CONFLICT",
            status_code=status.HTTP_409_CONFLICT,
        )
