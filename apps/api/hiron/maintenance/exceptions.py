"""Domain exceptions for Maintenance Subsystem."""

from fastapi import status

from hiron.common.exceptions import HironException


class MaintenancePermissionError(HironException):
    """Raised when non-org_admin user attempts to access maintenance operations."""

    def __init__(
        self, message: str = "Only org_admin users can perform maintenance operations"
    ) -> None:
        super().__init__(
            message=message,
            code="MAINTENANCE_PERMISSION_DENIED",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class MaintenanceExecutionError(HironException):
    """Raised when a maintenance task fails during execution."""

    def __init__(self, message: str = "Maintenance operation failed") -> None:
        super().__init__(
            message=message,
            code="MAINTENANCE_EXECUTION_FAILED",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
