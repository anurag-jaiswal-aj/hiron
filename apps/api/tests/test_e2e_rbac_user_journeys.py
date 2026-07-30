"""RBAC User Journeys E2E test verifying permission boundary enforcement per Phase 17."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.ai_usage.exceptions import InsufficientAIUsagePermissionsError
from hiron.ai_usage.repository import AIUsageRepository
from hiron.ai_usage.service import AIUsageService
from hiron.audit.exceptions import InsufficientAuditPermissionsError
from hiron.audit.repository import AuditRepository
from hiron.audit.service import AuditService
from hiron.security.service import InsufficientSecurityPermissionsError, SecurityService


@pytest.mark.asyncio
async def test_rbac_user_permission_boundaries() -> None:
    """Verify org_admin, recruiter, and member permission boundary enforcement across administrative subsystems."""
    session = AsyncMock()
    tenant_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    recruiter_id = uuid.uuid4()
    member_id = uuid.uuid4()

    usage_repo = AsyncMock(spec=AIUsageRepository)
    audit_repo = AsyncMock(spec=AuditRepository)

    ai_usage_service = AIUsageService(ai_usage_repository=usage_repo)
    audit_service = AuditService(audit_repository=audit_repo)
    security_service = SecurityService()

    # 1. AI Usage Analytics: org_admin allowed, recruiter/member forbidden (403)
    usage_repo.get_summary_metrics.return_value = (10.0, 1000, 5, 0.5)
    usage_repo.get_operation_breakdown.return_value = []
    usage_repo.get_daily_breakdown.return_value = []

    res_admin = await ai_usage_service.get_usage_summary(
        session=session, tenant_id=tenant_id, user_role="org_admin"
    )
    assert res_admin.data.total_cost_usd == 10.0

    with pytest.raises(InsufficientAIUsagePermissionsError):
        await ai_usage_service.get_usage_summary(
            session=session, tenant_id=tenant_id, user_role="recruiter"
        )

    with pytest.raises(InsufficientAIUsagePermissionsError):
        await ai_usage_service.get_usage_summary(
            session=session, tenant_id=tenant_id, user_role="member"
        )

    # 2. Audit Logs Scoping: org_admin sees all, recruiter scoped to own actions, member forbidden
    audit_repo.list_audit_logs.return_value = ([], False, None)

    # org_admin
    await audit_service.list_audit_logs(
        session=session, tenant_id=tenant_id, user_id=admin_id, user_role="org_admin"
    )
    _, kwargs_admin = audit_repo.list_audit_logs.call_args
    assert kwargs_admin["actor_id"] is None

    # recruiter (scoped to recruiter_id)
    await audit_service.list_audit_logs(
        session=session, tenant_id=tenant_id, user_id=recruiter_id, user_role="recruiter"
    )
    _, kwargs_rec = audit_repo.list_audit_logs.call_args
    assert kwargs_rec["actor_id"] == recruiter_id

    # member forbidden
    with pytest.raises(InsufficientAuditPermissionsError):
        await audit_service.list_audit_logs(
            session=session, tenant_id=tenant_id, user_id=member_id, user_role="member"
        )

    # 3. Security Audit: org_admin allowed, non-admins forbidden
    sec_admin = await security_service.run_security_audit(user_role="org_admin")
    assert sec_admin.data.compliance_status == "COMPLIANT"

    with pytest.raises(InsufficientSecurityPermissionsError):
        await security_service.run_security_audit(user_role="recruiter")
