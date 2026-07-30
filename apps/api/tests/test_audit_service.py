"""Service unit tests for AuditService RBAC permissions and entity audit log compilation."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.audit.exceptions import InsufficientAuditPermissionsError
from hiron.audit.service import AuditService


@pytest.mark.asyncio
async def test_recruiter_viewing_all_logs_overridden_to_own_actions() -> None:
    """Verify recruiter querying logs without specific entity_id is scoped to their own actor_id."""
    audit_repo = AsyncMock()
    service = AuditService(audit_repository=audit_repo)

    session = AsyncMock()
    tenant_id = uuid.uuid4()
    recruiter_user_id = uuid.uuid4()

    audit_repo.list_audit_logs.return_value = ([], False, None)

    await service.list_audit_logs(
        session=session,
        tenant_id=tenant_id,
        user_id=recruiter_user_id,
        user_role="recruiter",
    )

    # Scoped actor_id to recruiter_user_id
    audit_repo.list_audit_logs.assert_called_once()
    _, kwargs = audit_repo.list_audit_logs.call_args
    assert kwargs["actor_id"] == recruiter_user_id


@pytest.mark.asyncio
async def test_unauthorized_role_raises_403() -> None:
    """Verify unauthorized role raises InsufficientAuditPermissionsError."""
    service = AuditService()
    session = AsyncMock()

    with pytest.raises(InsufficientAuditPermissionsError):
        await service.list_audit_logs(
            session=session,
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            user_role="member",
        )
