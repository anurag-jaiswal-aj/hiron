"""Score domain specific exceptions."""

from fastapi import status

from hiron.common.exceptions import HironException


class InsufficientScorePermissionsError(HironException):
    """Raised when user role is not authorized for scoring operations."""

    def __init__(self, message: str = "Insufficient permissions for scoring operation") -> None:
        super().__init__(
            message=message,
            code="INSUFFICIENT_PERMISSIONS",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class AIServiceUnavailableError(HironException):
    """Raised when external LLM API is unavailable per API Contract §SCORE-1."""

    def __init__(self, message: str = "AI scoring service is currently unavailable") -> None:
        super().__init__(
            message=message,
            code="AI_SERVICE_UNAVAILABLE",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )


class AIScoringFailedError(HironException):
    """Raised when AI scoring fails after retries per API Contract §SCORE-1."""

    def __init__(self, message: str = "AI candidate scoring failed") -> None:
        super().__init__(
            message=message,
            code="AI_SCORING_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
