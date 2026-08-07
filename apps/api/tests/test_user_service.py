"""Unit test suite for UserService business logic and role validations."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.users.models import User
from hiron.users.service import (
    InsufficientUserPermissionsError,
    InvalidUserRoleError,
    LastAdminOperationError,
    UserEmailAlreadyExistsError,
    UserNotFoundError,
    UserService,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_user_repo() -> AsyncMock:
    """Fixture providing a mock UserRepository."""
    repo = AsyncMock()
    repo.get_by_email_and_tenant.return_value = None
    repo.get_by_id_and_tenant.return_value = None
    repo.count_active_admins_by_tenant.return_value = 2
    return repo


@pytest.fixture
def mock_token_repo() -> AsyncMock:
    """Fixture providing a mock RefreshTokenRepository."""
    repo = AsyncMock()
    repo.revoke_all_for_user.return_value = 0
    return repo


@pytest.mark.asyncio
async def test_get_user_by_id_not_found_raises(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify get_user_by_id raises UserNotFoundError when user is not found."""
    mock_user_repo.get_by_id_and_tenant.return_value = None
    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)

    with pytest.raises(UserNotFoundError):
        await service.get_user_by_id(mock_session, uuid.uuid4(), uuid.uuid4())


@pytest.mark.asyncio
async def test_create_user_success(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify create_user creates user with hashed password and persists entity."""
    tenant_id = uuid.uuid4()
    mock_user_repo.create.side_effect = lambda _session, user: user

    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)
    user = await service.create_user(
        session=mock_session,
        tenant_id=tenant_id,
        email="newuser@acme.com",
        full_name="New User",
        role="recruiter",
        password="SecurePassword123!",
    )

    assert user.email == "newuser@acme.com"
    assert user.role == "recruiter"
    assert user.password_hash is not None
    mock_user_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_duplicate_email_raises(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify create_user raises UserEmailAlreadyExistsError when email exists in tenant."""
    tenant_id = uuid.uuid4()
    mock_user_repo.get_by_email_and_tenant.return_value = User(
        tenant_id=tenant_id, email="existing@acme.com"
    )

    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)
    with pytest.raises(UserEmailAlreadyExistsError, match=r"existing@acme\.com"):
        await service.create_user(
            session=mock_session,
            tenant_id=tenant_id,
            email="existing@acme.com",
            full_name="Existing User",
            role="recruiter",
        )


@pytest.mark.asyncio
async def test_create_user_invalid_role_raises(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify create_user raises InvalidUserRoleError for invalid role string."""
    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)
    with pytest.raises(InvalidUserRoleError, match="super_admin"):
        await service.create_user(
            session=mock_session,
            tenant_id=uuid.uuid4(),
            email="test@acme.com",
            full_name="Test User",
            role="super_admin",
        )


@pytest.mark.asyncio
async def test_update_user_non_admin_updating_other_user_raises(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify non-admin cannot update another user's profile."""
    tenant_id = uuid.uuid4()
    target_id = uuid.uuid4()
    caller_id = uuid.uuid4()

    mock_user_repo.get_by_id_and_tenant.return_value = User(
        id=target_id, tenant_id=tenant_id, role="recruiter"
    )

    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)
    with pytest.raises(InsufficientUserPermissionsError):
        await service.update_user(
            session=mock_session,
            user_id=target_id,
            tenant_id=tenant_id,
            current_user_id=caller_id,
            current_user_role="recruiter",
            full_name="New Name",
        )


@pytest.mark.asyncio
async def test_update_user_demote_last_admin_raises(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify demoting the sole active org_admin raises LastAdminOperationError."""
    tenant_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    admin_user = User(id=admin_id, tenant_id=tenant_id, role="org_admin", is_active=True)
    mock_user_repo.get_by_id_and_tenant.return_value = admin_user
    mock_user_repo.count_active_admins_by_tenant.return_value = 1

    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)
    with pytest.raises(LastAdminOperationError, match="demotion"):
        await service.update_user(
            session=mock_session,
            user_id=admin_id,
            tenant_id=tenant_id,
            current_user_id=admin_id,
            current_user_role="org_admin",
            role="recruiter",
        )


@pytest.mark.asyncio
async def test_deactivate_last_admin_raises(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify deactivating the last active org_admin raises LastAdminOperationError."""
    tenant_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    admin_user = User(id=admin_id, tenant_id=tenant_id, role="org_admin", is_active=True)
    mock_user_repo.get_by_id_and_tenant.return_value = admin_user
    mock_user_repo.count_active_admins_by_tenant.return_value = 1

    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)
    with pytest.raises(LastAdminOperationError, match="deactivation"):
        await service.deactivate_user(
            session=mock_session,
            user_id=admin_id,
            tenant_id=tenant_id,
            current_user_id=admin_id,
            current_user_role="org_admin",
        )


@pytest.mark.asyncio
async def test_deactivate_user_success_revokes_tokens(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify deactivating user revokes all refresh tokens."""
    tenant_id = uuid.uuid4()
    target_id = uuid.uuid4()
    admin_id = uuid.uuid4()

    recruiter_user = User(id=target_id, tenant_id=tenant_id, role="recruiter", is_active=True)
    mock_user_repo.get_by_id_and_tenant.return_value = recruiter_user
    mock_user_repo.update.return_value = User(
        id=target_id, tenant_id=tenant_id, role="recruiter", is_active=False
    )

    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)
    updated = await service.deactivate_user(
        session=mock_session,
        user_id=target_id,
        tenant_id=tenant_id,
        current_user_id=admin_id,
        current_user_role="org_admin",
    )

    assert updated.is_active is False
    mock_token_repo.revoke_all_for_user.assert_awaited_once_with(mock_session, target_id)


@pytest.mark.asyncio
async def test_delete_user_not_admin_raises(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify non-admin cannot delete users."""
    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)
    with pytest.raises(InsufficientUserPermissionsError):
        await service.delete_user(
            session=mock_session,
            user_id=uuid.uuid4(),
            tenant_id=uuid.uuid4(),
            current_user_id=uuid.uuid4(),
            current_user_role="recruiter",
        )


@pytest.mark.asyncio
async def test_create_user_commits_transaction(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify create_user explicitly commits transaction on service level."""
    tenant_id = uuid.uuid4()
    mock_user_repo.create.side_effect = lambda _session, user: user

    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)
    await service.create_user(
        session=mock_session,
        tenant_id=tenant_id,
        email="tx_user@acme.com",
        full_name="Tx User",
        role="recruiter",
    )

    mock_session.commit.assert_awaited_once()
    mock_session.refresh.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_user_exception_does_not_commit(
    mock_session: AsyncMock,
    mock_user_repo: AsyncMock,
    mock_token_repo: AsyncMock,
) -> None:
    """Verify create_user does not commit when an exception is raised."""
    tenant_id = uuid.uuid4()
    mock_user_repo.get_by_email_and_tenant.return_value = User(
        tenant_id=tenant_id, email="dup@acme.com"
    )

    service = UserService(user_repo=mock_user_repo, token_repo=mock_token_repo)
    with pytest.raises(UserEmailAlreadyExistsError):
        await service.create_user(
            session=mock_session,
            tenant_id=tenant_id,
            email="dup@acme.com",
            full_name="Duplicate User",
            role="recruiter",
        )

    mock_session.commit.assert_not_called()

