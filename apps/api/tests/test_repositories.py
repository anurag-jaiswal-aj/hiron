"""Unit test suite for UserRepository and RefreshTokenRepository database query execution."""

from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from sqlalchemy.exc import SQLAlchemyError

from hiron.tokens.models import RefreshToken
from hiron.tokens.repository import RefreshTokenRepository
from hiron.users.models import User
from hiron.users.repository import UserRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    mock_result.rowcount = 0
    session.execute.return_value = mock_result
    return session


# ==============================================================================
# USER REPOSITORY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_user_repository_create_success(mock_session: AsyncMock) -> None:
    """Verify UserRepository.create adds entity to session and flushes."""
    repo = UserRepository()
    user = User(
        tenant_id=uuid.uuid4(),
        email="jane@acme.com",
        full_name="Jane Doe",
        role="recruiter",
    )
    
    created = await repo.create(mock_session, user)
    assert created == user
    mock_session.add.assert_called_once_with(user)
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_repository_create_flush_failure_raises(mock_session: AsyncMock) -> None:
    """Verify UserRepository.create propagates flush exception on failure."""
    repo = UserRepository()
    mock_session.flush.side_effect = SQLAlchemyError("Flush error")
    user = User(tenant_id=uuid.uuid4(), email="fail@acme.com", full_name="Fail", role="recruiter")

    with pytest.raises(SQLAlchemyError, match="Flush error"):
        await repo.create(mock_session, user)


@pytest.mark.asyncio
async def test_user_repository_get_by_email_success(mock_session: AsyncMock) -> None:
    """Verify UserRepository.get_by_email returns User entity when found."""
    repo = UserRepository()
    expected_user = User(tenant_id=uuid.uuid4(), email="user@acme.com", full_name="User", role="org_admin")
    mock_session.execute.return_value.scalar_one_or_none.return_value = expected_user

    user = await repo.get_by_email(mock_session, email="user@acme.com")
    assert user == expected_user


@pytest.mark.asyncio
async def test_user_repository_get_by_email_not_found_returns_none(mock_session: AsyncMock) -> None:
    """Verify UserRepository.get_by_email returns None when user does not exist."""
    repo = UserRepository()
    mock_session.execute.return_value.scalar_one_or_none.return_value = None

    user = await repo.get_by_email(mock_session, email="missing@acme.com")
    assert user is None


@pytest.mark.asyncio
async def test_user_repository_get_by_id_and_tenant_found(mock_session: AsyncMock) -> None:
    """Verify UserRepository.get_by_id_and_tenant returns User entity when found."""
    repo = UserRepository()
    expected_user = User(tenant_id=uuid.uuid4(), email="recruiter@acme.com", full_name="Recruiter", role="recruiter")
    mock_session.execute.return_value.scalar_one_or_none.return_value = expected_user

    result = await repo.get_by_id_and_tenant(mock_session, user_id=uuid.uuid4(), tenant_id=expected_user.tenant_id)
    assert result == expected_user


@pytest.mark.asyncio
async def test_user_repository_get_by_id_and_tenant_not_found(mock_session: AsyncMock) -> None:
    """Verify UserRepository.get_by_id_and_tenant returns None when user is not found."""
    repo = UserRepository()
    result = await repo.get_by_id_and_tenant(mock_session, user_id=uuid.uuid4(), tenant_id=uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_user_repository_list_by_tenant_returns_list(mock_session: AsyncMock) -> None:
    """Verify UserRepository.list_by_tenant returns sequence list of User entities."""
    repo = UserRepository()
    user1 = User(tenant_id=uuid.uuid4(), email="u1@acme.com", full_name="U1", role="recruiter")
    user2 = User(tenant_id=uuid.uuid4(), email="u2@acme.com", full_name="U2", role="hiring_manager")
    mock_session.execute.return_value.scalars.return_value.all.return_value = [user1, user2]

    users = await repo.list_by_tenant(mock_session, tenant_id=uuid.uuid4(), limit=10, offset=0)
    assert len(users) == 2
    assert users[0] == user1
    assert users[1] == user2


# ==============================================================================
# REFRESH TOKEN REPOSITORY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_refresh_token_repository_create_success(mock_session: AsyncMock) -> None:
    """Verify RefreshTokenRepository.create adds token entity to session and flushes."""
    repo = RefreshTokenRepository()
    token = RefreshToken(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), token_hash="hash_123", expires_at=None)

    created = await repo.create(mock_session, token)
    assert created == token
    mock_session.add.assert_called_once_with(token)
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_refresh_token_repository_get_by_token_hash_found(mock_session: AsyncMock) -> None:
    """Verify RefreshTokenRepository.get_by_token_hash returns RefreshToken entity when found."""
    repo = RefreshTokenRepository()
    expected_token = RefreshToken(user_id=uuid.uuid4(), tenant_id=uuid.uuid4(), token_hash="hash_abc", expires_at=None)
    mock_session.execute.return_value.scalar_one_or_none.return_value = expected_token

    result = await repo.get_by_token_hash(mock_session, token_hash="hash_abc")
    assert result == expected_token


@pytest.mark.asyncio
async def test_refresh_token_repository_revoke_by_token_hash_returns_false_when_not_found(
    mock_session: AsyncMock,
) -> None:
    """Verify RefreshTokenRepository.revoke_by_token_hash returns False when rowcount == 0."""
    repo = RefreshTokenRepository()
    mock_session.execute.return_value.rowcount = 0

    revoked = await repo.revoke_by_token_hash(mock_session, token_hash="missing_hash")
    assert revoked is False


@pytest.mark.asyncio
async def test_refresh_token_repository_revoke_by_token_hash_returns_true_when_revoked(
    mock_session: AsyncMock,
) -> None:
    """Verify RefreshTokenRepository.revoke_by_token_hash returns True when rowcount > 0."""
    repo = RefreshTokenRepository()
    mock_session.execute.return_value.rowcount = 1

    revoked = await repo.revoke_by_token_hash(mock_session, token_hash="active_hash")
    assert revoked is True


@pytest.mark.asyncio
async def test_refresh_token_repository_delete_expired_returns_zero(mock_session: AsyncMock) -> None:
    """Verify RefreshTokenRepository.delete_expired returns 0 when no expired tokens exist."""
    repo = RefreshTokenRepository()
    mock_session.execute.return_value.rowcount = 0

    deleted = await repo.delete_expired(mock_session)
    assert deleted == 0
