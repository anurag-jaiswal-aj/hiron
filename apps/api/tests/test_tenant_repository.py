"""Unit test suite for TenantRepository database query execution."""

from unittest.mock import AsyncMock, MagicMock
import uuid

import pytest
from sqlalchemy.exc import SQLAlchemyError

from hiron.tenants.models import Tenant
from hiron.tenants.repository import TenantRepository


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


@pytest.mark.asyncio
async def test_tenant_repository_create_success(mock_session: AsyncMock) -> None:
    """Verify TenantRepository.create adds tenant entity to session and flushes."""
    repo = TenantRepository()
    tenant = Tenant(
        name="Acme Corp",
        slug="acme-corp",
        plan="starter",
    )

    created = await repo.create(mock_session, tenant)
    assert created == tenant
    mock_session.add.assert_called_once_with(tenant)
    mock_session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_tenant_repository_create_flush_failure_raises(mock_session: AsyncMock) -> None:
    """Verify TenantRepository.create propagates flush exception on failure."""
    repo = TenantRepository()
    mock_session.flush.side_effect = SQLAlchemyError("Flush error")
    tenant = Tenant(name="Fail Corp", slug="fail-corp", plan="starter")

    with pytest.raises(SQLAlchemyError, match="Flush error"):
        await repo.create(mock_session, tenant)


@pytest.mark.asyncio
async def test_tenant_repository_get_by_id_found(mock_session: AsyncMock) -> None:
    """Verify TenantRepository.get_by_id returns Tenant entity when found."""
    repo = TenantRepository()
    tenant_id = uuid.uuid4()
    expected_tenant = Tenant(id=tenant_id, name="Acme", slug="acme", plan="professional")
    mock_session.execute.return_value.scalar_one_or_none.return_value = expected_tenant

    result = await repo.get_by_id(mock_session, tenant_id)
    assert result == expected_tenant
    mock_session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_tenant_repository_get_by_id_not_found(mock_session: AsyncMock) -> None:
    """Verify TenantRepository.get_by_id returns None when tenant is not found."""
    repo = TenantRepository()
    mock_session.execute.return_value.scalar_one_or_none.return_value = None

    result = await repo.get_by_id(mock_session, uuid.uuid4())
    assert result is None


@pytest.mark.asyncio
async def test_tenant_repository_get_by_slug_found(mock_session: AsyncMock) -> None:
    """Verify TenantRepository.get_by_slug returns Tenant entity matching slug."""
    repo = TenantRepository()
    expected_tenant = Tenant(name="Acme Corp", slug="acme-corp", plan="enterprise")
    mock_session.execute.return_value.scalar_one_or_none.return_value = expected_tenant

    result = await repo.get_by_slug(mock_session, "acme-corp")
    assert result == expected_tenant


@pytest.mark.asyncio
async def test_tenant_repository_get_by_slug_not_found(mock_session: AsyncMock) -> None:
    """Verify TenantRepository.get_by_slug returns None when slug is not found."""
    repo = TenantRepository()
    mock_session.execute.return_value.scalar_one_or_none.return_value = None

    result = await repo.get_by_slug(mock_session, "nonexistent-slug")
    assert result is None


@pytest.mark.asyncio
async def test_tenant_repository_list_active(mock_session: AsyncMock) -> None:
    """Verify TenantRepository.list_active returns sequence of active Tenant entities."""
    repo = TenantRepository()
    t1 = Tenant(name="T1", slug="t1", is_active=True)
    t2 = Tenant(name="T2", slug="t2", is_active=True)
    mock_session.execute.return_value.scalars.return_value.all.return_value = [t1, t2]

    active_tenants = await repo.list_active(mock_session, limit=10, offset=0)
    assert len(active_tenants) == 2
    assert active_tenants[0] == t1
    assert active_tenants[1] == t2


@pytest.mark.asyncio
async def test_tenant_repository_update_success(mock_session: AsyncMock) -> None:
    """Verify TenantRepository.update executes update query and returns updated entity."""
    repo = TenantRepository()
    tenant_id = uuid.uuid4()
    updated_tenant = Tenant(id=tenant_id, name="Acme Inc", slug="acme-corp", plan="professional")
    mock_session.execute.return_value.scalar_one_or_none.return_value = updated_tenant

    result = await repo.update(mock_session, tenant_id=tenant_id, name="Acme Inc", plan="professional")
    assert result == updated_tenant
    assert mock_session.execute.call_count == 2


@pytest.mark.asyncio
async def test_tenant_repository_delete_success(mock_session: AsyncMock) -> None:
    """Verify TenantRepository.delete returns True when tenant row is deleted."""
    repo = TenantRepository()
    mock_session.execute.return_value.rowcount = 1

    deleted = await repo.delete(mock_session, uuid.uuid4())
    assert deleted is True


@pytest.mark.asyncio
async def test_tenant_repository_delete_not_found(mock_session: AsyncMock) -> None:
    """Verify TenantRepository.delete returns False when rowcount is 0."""
    repo = TenantRepository()
    mock_session.execute.return_value.rowcount = 0

    deleted = await repo.delete(mock_session, uuid.uuid4())
    assert deleted is False
