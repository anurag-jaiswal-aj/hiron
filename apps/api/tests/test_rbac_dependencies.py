"""Unit test suite for Role-Based Access Control (RBAC) authorization dependencies (require_role)."""

import uuid

import pytest

from hiron.auth.dependencies import require_role
from hiron.common.exceptions import PermissionDeniedException
from hiron.users.models import User


@pytest.mark.asyncio
async def test_require_role_allowed_single_role_success() -> None:
    """Verify require_role returns User when current_user.role matches allowed role."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="admin@acme.com",
        full_name="Admin User",
        role="org_admin",
        is_active=True,
    )
    checker = require_role("org_admin")
    
    result = await checker(current_user=user)
    assert result == user


@pytest.mark.asyncio
async def test_require_role_allowed_multiple_roles_success() -> None:
    """Verify require_role returns User when current_user.role is one of multiple allowed roles."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="recruiter@acme.com",
        full_name="Recruiter User",
        role="recruiter",
        is_active=True,
    )
    checker = require_role("org_admin", "recruiter")
    
    result = await checker(current_user=user)
    assert result == user


@pytest.mark.asyncio
async def test_require_role_disallowed_role_raises_permission_denied_exception() -> None:
    """Verify require_role raises PermissionDeniedException (HTTP 403) when user role is not allowed."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="manager@acme.com",
        full_name="Hiring Manager",
        role="hiring_manager",
        is_active=True,
    )
    checker = require_role("org_admin", "recruiter")
    
    with pytest.raises(PermissionDeniedException) as exc_info:
        await checker(current_user=user)
        
    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "INSUFFICIENT_PERMISSIONS"


@pytest.mark.asyncio
async def test_require_role_empty_allowed_roles_raises_permission_denied_exception() -> None:
    """Verify require_role raises PermissionDeniedException when no roles are allowed."""
    user = User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="admin@acme.com",
        full_name="Admin User",
        role="org_admin",
        is_active=True,
    )
    checker = require_role()
    
    with pytest.raises(PermissionDeniedException):
        await checker(current_user=user)
