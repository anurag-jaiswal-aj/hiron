"""Thin FastAPI router for Security Hardening & Audit per Phase 16."""

from fastapi import APIRouter, Depends, status

from hiron.auth.dependencies import get_current_user
from hiron.security.schemas import SecurityAuditReportResponse
from hiron.security.service import SecurityService
from hiron.users.models import User

router = APIRouter(tags=["Security & Hardening"])


def get_security_service() -> SecurityService:
    """Dependency provider for SecurityService."""
    return SecurityService()


@router.get(
    "/security/audit",
    response_model=SecurityAuditReportResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Security Controls Audit Report (Phase 16)",
)
async def get_security_audit_endpoint(
    current_user: User = Depends(get_current_user),
    service: SecurityService = Depends(get_security_service),
) -> SecurityAuditReportResponse:
    """Get comprehensive security controls compliance and audit report."""
    return await service.run_security_audit(user_role=current_user.role)
