"""Unit test suite for authentication FastAPI dependencies (get_current_user)."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from jwt.exceptions import ExpiredSignatureError

from hiron.auth.dependencies import get_current_user
from hiron.auth.service import AccountDisabledError, AuthenticationError
from hiron.users.models import User
from hiron.users.repository import UserRepository


@pytest.fixture
def mock_db() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    """Fixture providing a mock UserRepository."""
    return AsyncMock(spec=UserRepository)


@pytest.mark.asyncio
async def test_get_current_user_success(
    mock_db: AsyncMock,
    mock_user_repo: AsyncMock,
) -> None:
    """Verify get_current_user extracts Bearer token, validates claims, lookups user, and returns User entity."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="jane@acme.com",
        full_name="Jane Smith",
        role="recruiter",
        is_active=True,
    )
    mock_user_repo.get_by_id_and_tenant.return_value = mock_user

    with patch(
        "hiron.auth.dependencies.verify_token",
        return_value={"sub": str(user_id), "tenantId": str(tenant_id), "type": "access"},
    ):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_access_jwt")

        current_user = await get_current_user(
            db=mock_db, user_repo=mock_user_repo, credentials=credentials
        )

        assert current_user == mock_user
        mock_user_repo.get_by_id_and_tenant.assert_awaited_once_with(
            session=mock_db,
            user_id=user_id,
            tenant_id=tenant_id,
        )


@pytest.mark.asyncio
async def test_get_current_user_missing_credentials_raises_authentication_error(
    mock_db: AsyncMock,
    mock_user_repo: AsyncMock,
) -> None:
    """Verify get_current_user raises AuthenticationError when Authorization header is missing."""
    with pytest.raises(AuthenticationError, match="Missing Authorization header"):
        await get_current_user(db=mock_db, user_repo=mock_user_repo, credentials=None)


@pytest.mark.asyncio
async def test_get_current_user_invalid_token_raises_authentication_error(
    mock_db: AsyncMock,
    mock_user_repo: AsyncMock,
) -> None:
    """Verify get_current_user raises AuthenticationError when verify_token fails."""
    with patch(
        "hiron.auth.dependencies.verify_token", side_effect=Exception("Invalid token signature")
    ):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid_jwt")

        with pytest.raises(AuthenticationError, match="Invalid authentication token"):
            await get_current_user(db=mock_db, user_repo=mock_user_repo, credentials=credentials)


@pytest.mark.asyncio
async def test_get_current_user_expired_token_raises_authentication_error(
    mock_db: AsyncMock,
    mock_user_repo: AsyncMock,
) -> None:
    """Verify get_current_user raises AuthenticationError when access token has expired."""
    with patch(
        "hiron.auth.dependencies.verify_token", side_effect=ExpiredSignatureError("Signature has expired")
    ):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="expired_jwt")

        with pytest.raises(AuthenticationError, match="Access token has expired"):
            await get_current_user(db=mock_db, user_repo=mock_user_repo, credentials=credentials)


@pytest.mark.asyncio
async def test_get_current_user_not_found_raises_authentication_error(
    mock_db: AsyncMock,
    mock_user_repo: AsyncMock,
) -> None:
    """Verify get_current_user raises AuthenticationError when user is not found in database."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    mock_user_repo.get_by_id_and_tenant.return_value = None

    with patch(
        "hiron.auth.dependencies.verify_token",
        return_value={"sub": str(user_id), "tenantId": str(tenant_id), "type": "access"},
    ):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_jwt")

        with pytest.raises(AuthenticationError, match="Authenticated user not found"):
            await get_current_user(db=mock_db, user_repo=mock_user_repo, credentials=credentials)


@pytest.mark.asyncio
async def test_get_current_user_inactive_user_raises_account_disabled_error(
    mock_db: AsyncMock,
    mock_user_repo: AsyncMock,
) -> None:
    """Verify get_current_user raises AccountDisabledError when user is_active is False."""
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="inactive@acme.com",
        full_name="Inactive User",
        role="recruiter",
        is_active=False,
    )
    mock_user_repo.get_by_id_and_tenant.return_value = mock_user

    with patch(
        "hiron.auth.dependencies.verify_token",
        return_value={"sub": str(user_id), "tenantId": str(tenant_id), "type": "access"},
    ):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="valid_jwt")
        with pytest.raises(AccountDisabledError, match="Account is deactivated"):
            await get_current_user(db=mock_db, user_repo=mock_user_repo, credentials=credentials)
