"""Unit test suite for AuthService business logic execution."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError

from hiron.auth.service import AccountDisabledError, AuthenticationError, AuthService
from hiron.tokens.repository import RefreshTokenRepository
from hiron.users.models import User
from hiron.users.repository import UserRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    """Fixture providing a mock UserRepository."""
    return AsyncMock(spec=UserRepository)


@pytest.fixture
def mock_token_repo() -> AsyncMock:
    """Fixture providing a mock RefreshTokenRepository."""
    return AsyncMock(spec=RefreshTokenRepository)


# ==============================================================================
# AUTHENTICATE USER TESTS
# ==============================================================================


@pytest.mark.asyncio
async def test_authenticate_user_success(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify authenticate_user succeeds when email, password, and active account match."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="jane@acme.com",
        full_name="Jane Doe",
        role="recruiter",
        password_hash="$argon2id$v=19$m=65536,t=3,p=4$dummy_hash",
        is_active=True,
    )
    mock_user_repo.get_by_email_and_tenant.return_value = mock_user

    service = AuthService(user_repo=mock_user_repo, token_repo=mock_token_repo)

    with patch("hiron.auth.service.verify_password", return_value=True) as mock_verify:
        authenticated_user = await service.authenticate_user(
            session=mock_session,
            email="jane@acme.com",
            password="CorrectPassword123!",
            tenant_id=tenant_id,
        )

        assert authenticated_user == mock_user
        mock_user_repo.get_by_email_and_tenant.assert_awaited_once_with(
            session=mock_session,
            email="jane@acme.com",
            tenant_id=tenant_id,
        )
        mock_verify.assert_called_once_with("CorrectPassword123!", mock_user.password_hash)


@pytest.mark.asyncio
async def test_authenticate_user_not_found_raises_authentication_error(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify authenticate_user raises AuthenticationError when user does not exist."""
    tenant_id = uuid.uuid4()
    mock_user_repo.get_by_email_and_tenant.return_value = None

    service = AuthService(user_repo=mock_user_repo, token_repo=mock_token_repo)

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        await service.authenticate_user(
            session=mock_session,
            email="nonexistent@acme.com",
            password="Password123!",
            tenant_id=tenant_id,
        )


@pytest.mark.asyncio
async def test_authenticate_user_inactive_raises_account_disabled_error(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify authenticate_user raises AccountDisabledError when user is_active is False."""
    tenant_id = uuid.uuid4()
    mock_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="inactive@acme.com",
        full_name="Inactive User",
        role="recruiter",
        password_hash="$argon2id$hash",
        is_active=False,
    )
    mock_user_repo.get_by_email_and_tenant.return_value = mock_user

    service = AuthService(user_repo=mock_user_repo, token_repo=mock_token_repo)

    with pytest.raises(AccountDisabledError, match="Account is deactivated"):
        await service.authenticate_user(
            session=mock_session,
            email="inactive@acme.com",
            password="Password123!",
            tenant_id=tenant_id,
        )


@pytest.mark.asyncio
async def test_authenticate_user_no_password_hash_raises_authentication_error(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify authenticate_user raises AuthenticationError for OAuth-only users with NULL password_hash."""
    tenant_id = uuid.uuid4()
    mock_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="oauth@acme.com",
        full_name="OAuth User",
        role="recruiter",
        password_hash=None,
        is_active=True,
    )
    mock_user_repo.get_by_email_and_tenant.return_value = mock_user

    service = AuthService(user_repo=mock_user_repo, token_repo=mock_token_repo)

    with pytest.raises(AuthenticationError, match="Invalid email or password"):
        await service.authenticate_user(
            session=mock_session,
            email="oauth@acme.com",
            password="Password123!",
            tenant_id=tenant_id,
        )


@pytest.mark.asyncio
async def test_authenticate_user_wrong_password_raises_authentication_error(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify authenticate_user raises AuthenticationError when password verification fails."""
    tenant_id = uuid.uuid4()
    mock_user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="user@acme.com",
        full_name="User",
        role="recruiter",
        password_hash="$argon2id$hash",
        is_active=True,
    )
    mock_user_repo.get_by_email_and_tenant.return_value = mock_user

    service = AuthService(user_repo=mock_user_repo, token_repo=mock_token_repo)

    with patch("hiron.auth.service.verify_password", return_value=False):
        with pytest.raises(AuthenticationError, match="Invalid email or password"):
            await service.authenticate_user(
                session=mock_session,
                email="user@acme.com",
                password="WrongPassword123!",
                tenant_id=tenant_id,
            )


# ==============================================================================
# CREATE AUTH TOKENS TESTS & FAILURE PATHS
# ==============================================================================


@pytest.mark.asyncio
async def test_create_auth_tokens_success(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify create_auth_tokens creates access token, refresh token, persists hashed token, and updates last_login_at via repo."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="jane@acme.com",
        full_name="Jane Doe",
        role="recruiter",
        password_hash="$argon2id$hash",
        is_active=True,
    )

    service = AuthService(user_repo=mock_user_repo, token_repo=mock_token_repo)

    with (
        patch(
            "hiron.auth.service.create_access_token", return_value="dummy_access_token"
        ) as mock_access,
        patch(
            "hiron.auth.service.create_refresh_token", return_value="dummy_refresh_token"
        ) as mock_refresh,
    ):
        access_tok, refresh_tok = await service.create_auth_tokens(
            session=mock_session,
            user=mock_user,
            user_agent="Mozilla/5.0",
            ip_address="192.168.1.1",
        )

        assert access_tok == "dummy_access_token"
        assert refresh_tok == "dummy_refresh_token"

        mock_access.assert_called_once_with(
            user_id=user_id,
            tenant_id=tenant_id,
            email="jane@acme.com",
            role="recruiter",
        )
        mock_refresh.assert_called_once()
        mock_token_repo.create.assert_awaited_once()
        mock_user_repo.update_last_login.assert_awaited_once_with(
            session=mock_session, user_id=user_id
        )


@pytest.mark.asyncio
async def test_create_auth_tokens_jwt_generation_failure(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify create_auth_tokens propagates error and prevents persistence if JWT generation fails."""
    mock_user = User(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="u@acme.com", full_name="U", role="recruiter"
    )
    service = AuthService(user_repo=mock_user_repo, token_repo=mock_token_repo)

    with patch(
        "hiron.auth.service.create_access_token", side_effect=ValueError("JWT config error")
    ):
        with pytest.raises(ValueError, match="JWT config error"):
            await service.create_auth_tokens(mock_session, mock_user)

        mock_token_repo.create.assert_not_called()
        mock_user_repo.update_last_login.assert_not_called()


@pytest.mark.asyncio
async def test_create_auth_tokens_token_repo_create_failure(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify create_auth_tokens propagates database exception when token_repo.create fails."""
    mock_user = User(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="u@acme.com", full_name="U", role="recruiter"
    )
    mock_token_repo.create.side_effect = SQLAlchemyError("DB Error")

    service = AuthService(user_repo=mock_user_repo, token_repo=mock_token_repo)

    with (
        patch("hiron.auth.service.create_access_token", return_value="access_token"),
        patch("hiron.auth.service.create_refresh_token", return_value="refresh_token"),
    ):
        with pytest.raises(SQLAlchemyError, match="DB Error"):
            await service.create_auth_tokens(mock_session, mock_user)

        mock_user_repo.update_last_login.assert_not_called()


@pytest.mark.asyncio
async def test_create_auth_tokens_update_last_login_failure(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify create_auth_tokens propagates database exception when update_last_login fails."""
    mock_user = User(
        id=uuid.uuid4(), tenant_id=uuid.uuid4(), email="u@acme.com", full_name="U", role="recruiter"
    )
    mock_user_repo.update_last_login.side_effect = SQLAlchemyError("Update error")

    service = AuthService(user_repo=mock_user_repo, token_repo=mock_token_repo)

    with (
        patch("hiron.auth.service.create_access_token", return_value="access_token"),
        patch("hiron.auth.service.create_refresh_token", return_value="refresh_token"),
    ):
        with pytest.raises(SQLAlchemyError, match="Update error"):
            await service.create_auth_tokens(mock_session, mock_user)
