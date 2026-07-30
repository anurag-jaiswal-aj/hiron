"""Embedding domain specific exceptions."""

from fastapi import status

from hiron.common.exceptions import HironException


class InsufficientEmbeddingPermissionsError(HironException):
    """Raised when user role is not authorized for embedding operations."""

    def __init__(self, message: str = "Insufficient permissions for embedding operation") -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class EmbeddingGenerationFailedError(HironException):
    """Raised when embedding generation vector model execution fails."""

    def __init__(self, message: str = "Embedding generation failed") -> None:
        super().__init__(
            message=message,
            code="EMBEDDING_GENERATION_FAILED",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )
