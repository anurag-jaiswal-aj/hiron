"""Unit test suite for UserRepository database operations."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from hiron.users.models import User
from hiron.users.repository import UserRepository


@pytest.fixture
def mock_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar_one.return_value = 0
    mock_result.scalars.return_value.all.return_value = []
    mock_result.rowcount = 0
    session.execute.return_value = mock_result
    return session


@pytest.mark.asyncio
async def test_user_repository_create_success(mock_session: AsyncMock) -> None:
    """Verify UserRepository.create adds User entity to session and flushes."""
    repo = UserRepository()
    user = User(
        tenant_id=uuid.uuid4(),
        email="alice@acme.com",
        full_name="Alice Smith",
        role="org_admin",
    )

    created = await repo.create(mock_session, user)
    assert created == user
    mock_session.add.assert_called_once_with(user)
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_user_repository_get_by_id_and_tenant_found(mock_session: AsyncMock) -> None:
    """Verify get_by_id_and_tenant returns User entity when found."""
    repo = UserRepository()
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    expected_user = User(id=user_id, tenant_id=tenant_id, email="bob@acme.com", role="recruiter")
    mock_session.execute.return_value.scalar_one_or_none.return_value = expected_user

    user = await repo.get_by_id_and_tenant(mock_session, user_id, tenant_id)
    assert user == expected_user


@pytest.mark.asyncio
async def test_user_repository_get_by_email_and_tenant_found(mock_session: AsyncMock) -> None:
    """Verify get_by_email_and_tenant returns User entity matching email and tenant_id."""
    repo = UserRepository()
    tenant_id = uuid.uuid4()
    expected_user = User(tenant_id=tenant_id, email="charlie@acme.com", role="hiring_manager")
    mock_session.execute.return_value.scalar_one_or_none.return_value = expected_user

    user = await repo.get_by_email_and_tenant(mock_session, "charlie@acme.com", tenant_id)
    assert user == expected_user


@pytest.mark.asyncio
async def test_user_repository_list_by_tenant_with_pagination(mock_session: AsyncMock) -> None:
    """Verify list_by_tenant returns sequence of users and total count."""
    repo = UserRepository()
    tenant_id = uuid.uuid4()
    u1 = User(tenant_id=tenant_id, email="u1@acme.com", role="recruiter")
    u2 = User(tenant_id=tenant_id, email="u2@acme.com", role="recruiter")

    mock_count_res = MagicMock()
    mock_count_res.scalar_one.return_value = 2

    mock_items_res = MagicMock()
    mock_items_res.scalars.return_value.all.return_value = [u1, u2]

    mock_session.execute.side_effect = [mock_count_res, mock_items_res]

    users, total = await repo.list_by_tenant(
        mock_session,
        tenant_id=tenant_id,
        role="recruiter",
        is_active=True,
        limit=10,
        offset=0,
    )
    assert len(users) == 2
    assert total == 2
    assert users[0] == u1


@pytest.mark.asyncio
async def test_user_repository_count_active_admins(mock_session: AsyncMock) -> None:
    """Verify count_active_admins_by_tenant executes count query and returns scalar int."""
    repo = UserRepository()
    mock_session.execute.return_value.scalar_one.return_value = 1

    count = await repo.count_active_admins_by_tenant(mock_session, uuid.uuid4())
    assert count == 1


@pytest.mark.asyncio
async def test_user_repository_update_success(mock_session: AsyncMock) -> None:
    """Verify UserRepository.update executes update statement and returns updated user."""
    repo = UserRepository()
    user_id = uuid.uuid4()
    tenant_id = uuid.uuid4()
    updated_user = User(id=user_id, tenant_id=tenant_id, full_name="Updated Name")
    mock_session.execute.return_value.scalar_one_or_none.return_value = updated_user

    res = await repo.update(
        mock_session, user_id=user_id, tenant_id=tenant_id, full_name="Updated Name"
    )
    assert res == updated_user


@pytest.mark.asyncio
async def test_user_repository_delete_success(mock_session: AsyncMock) -> None:
    """Verify UserRepository.delete returns True when row is deleted."""
    repo = UserRepository()
    mock_session.execute.return_value.rowcount = 1

    deleted = await repo.delete(mock_session, uuid.uuid4(), uuid.uuid4())
    assert deleted is True
