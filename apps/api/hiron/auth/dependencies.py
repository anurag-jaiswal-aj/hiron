"""FastAPI authentication and authorization (RBAC) dependencies per API Contract §4 & Engineering Guidelines §16.1."""

import uuid
from collections.abc import Sequence
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError
from sqlalchemy.ext.asyncio import AsyncSession

from hiron.auth.service import AccountDisabledError, AuthenticationError
from hiron.common.exceptions import PermissionDeniedException
from hiron.core.database import get_db_session
from hiron.core.jwt import verify_token
from hiron.users.models import User
from hiron.users.repository import UserRepository

# HTTP Bearer scheme for Authorization header extraction
http_bearer = HTTPBearer(auto_error=False)


def get_user_repository() -> UserRepository:
    """Dependency provider for UserRepository."""
    return UserRepository()


async def get_current_user(
    db: Annotated[AsyncSession, Depends(get_db_session)],
    user_repo: Annotated[UserRepository, Depends(get_user_repository)],
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(http_bearer)] = None,
) -> User:
    """Extract and validate the currently authenticated User entity from the Authorization Bearer header.

    Workflow per API Contract §4 & §5:
    1. Extract Bearer JWT access token from Authorization header.
    2. Validate JWT signature, expiration, and type ("access").
    3. Extract user_id (sub) and tenant_id (tenantId) claims.
    4. Fetch user via UserRepository.get_by_id_and_tenant().
    5. Verify user exists and account is active (is_active = True).

    Args:
        db: Active AsyncSession database handle.
        user_repo: Injected UserRepository instance.
        credentials: Optional HTTPAuthorizationCredentials provided by HTTPBearer dependency.

    Returns:
        Authenticated User entity.

    Raises:
        AuthenticationError: If Authorization header is missing, malformed, expired, or invalid.
        AccountDisabledError: If user account is deactivated (is_active = False).
    """
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Missing Authorization header")

    token = credentials.credentials

    # 1. Validate access token signature, expiry, and claims
    try:
        payload = verify_token(token, expected_type="access")
    except ExpiredSignatureError as exc:
        raise AuthenticationError("Access token has expired") from exc
    except InvalidTokenError as exc:
        raise AuthenticationError("Invalid authentication token") from exc
    except Exception as exc:
        raise AuthenticationError("Invalid authentication token") from exc

    # 2. Extract sub (user_id) and tenantId
    try:
        user_id = uuid.UUID(payload["sub"])
        tenant_id = uuid.UUID(payload["tenantId"])
    except (KeyError, ValueError) as exc:
        raise AuthenticationError("Malformed token payload") from exc

    # 3. Lookup user with strict tenant context validation
    user = await user_repo.get_by_id_and_tenant(session=db, user_id=user_id, tenant_id=tenant_id)
    if not user:
        raise AuthenticationError("Authenticated user not found")

    # 4. Verify account active status
    if not user.is_active:
        raise AccountDisabledError()

    return user


class RoleChecker:
    """FastAPI callable dependency checking user roles against allowed roles per API Contract §4."""

    def __init__(self, allowed_roles: Sequence[str]) -> None:
        """Initialize RoleChecker with allowed roles.

        Args:
            allowed_roles: Sequence of role strings (e.g. ['org_admin', 'recruiter']).
        """
        self.allowed_roles = set(allowed_roles)

    async def __call__(self, current_user: Annotated[User, Depends(get_current_user)]) -> User:
        """Enforce role check on the currently authenticated user.

        Args:
            current_user: Authenticated User entity from get_current_user dependency.

        Returns:
            Authenticated User entity if role check succeeds.

        Raises:
            PermissionDeniedException: If current_user.role is not in allowed_roles (HTTP 403).
        """
        if current_user.role not in self.allowed_roles:
            raise PermissionDeniedException("Insufficient permissions for this action")
        return current_user


def require_role(*allowed_roles: str) -> RoleChecker:
    """Dependency factory returning a RoleChecker for the specified allowed roles.

    Example:
        @router.get("/jobs", dependencies=[Depends(require_role("org_admin", "recruiter"))])
        async def list_jobs(...):
            ...
    """
    return RoleChecker(allowed_roles)
