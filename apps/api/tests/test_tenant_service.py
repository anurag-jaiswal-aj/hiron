"""Unit test suite for TenantService business logic and repository orchestration."""

import uuid
from unittest.mock import AsyncMock

import pytest

from hiron.tenants.models import Tenant
from hiron.tenants.repository import TenantRepository
from hiron.tenants.service import (
    InvalidTenantPlanError,
    TenantNotFoundError,
    TenantService,
    TenantSlugAlreadyExistsError,
)


@pytest.fixture
def mock_session() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_tenant_repo() -> AsyncMock:
    """Fixture providing a mock TenantRepository."""
    return AsyncMock(spec=TenantRepository)


@pytest.fixture
def admin_user_id() -> uuid.UUID:
    """Fixture providing a deterministic org_admin user ID for tenant administrative operations."""
    return uuid.UUID("11111111-1111-1111-1111-111111111111")


@pytest.mark.asyncio
async def test_create_tenant_normalizes_slug_before_checking_uniqueness(
    mock_session: AsyncMock,
    mock_tenant_repo: AsyncMock,
    admin_user_id: uuid.UUID,
) -> None:
    """Verify create_tenant normalizes (lowercases/strips) slug before checking uniqueness."""
    mock_tenant_repo.get_by_slug.return_value = None
    created_tenant = Tenant(id=uuid.uuid4(), name="Acme Corp", slug="acme-corp", plan="starter")
    mock_tenant_repo.create.return_value = created_tenant

    service = TenantService(tenant_repo=mock_tenant_repo)
    result = await service.create_tenant(
        mock_session, user_id=admin_user_id, name="Acme Corp", slug="  ACME-CORP  ", plan="starter"
    )

    assert result == created_tenant
    mock_tenant_repo.get_by_slug.assert_awaited_once_with(mock_session, "acme-corp")
    mock_tenant_repo.create.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_tenant_duplicate_slug_raises_error(
    mock_session: AsyncMock,
    mock_tenant_repo: AsyncMock,
    admin_user_id: uuid.UUID,
) -> None:
    """Verify create_tenant raises TenantSlugAlreadyExistsError when normalized slug exists."""
    existing_tenant = Tenant(
        id=uuid.uuid4(), name="Existing", slug="duplicate-slug", plan="starter"
    )
    mock_tenant_repo.get_by_slug.return_value = existing_tenant

    service = TenantService(tenant_repo=mock_tenant_repo)
    with pytest.raises(TenantSlugAlreadyExistsError, match="duplicate-slug"):
        await service.create_tenant(
            mock_session, user_id=admin_user_id, name="New", slug="DUPLICATE-SLUG", plan="starter"
        )

    mock_tenant_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_create_tenant_invalid_plan_raises_error(
    mock_session: AsyncMock,
    mock_tenant_repo: AsyncMock,
    admin_user_id: uuid.UUID,
) -> None:
    """Verify create_tenant raises InvalidTenantPlanError when plan is invalid."""
    service = TenantService(tenant_repo=mock_tenant_repo)
    with pytest.raises(InvalidTenantPlanError, match="invalid_plan"):
        await service.create_tenant(
            mock_session, user_id=admin_user_id, name="New", slug="new-slug", plan="invalid_plan"
        )

    mock_tenant_repo.get_by_slug.assert_not_called()
    mock_tenant_repo.create.assert_not_called()


@pytest.mark.asyncio
async def test_get_tenant_by_id_success(
    mock_session: AsyncMock, mock_tenant_repo: AsyncMock
) -> None:
    """Verify get_tenant_by_id returns Tenant entity when found."""
    tenant_id = uuid.uuid4()
    mock_tenant = Tenant(id=tenant_id, name="Acme", slug="acme", plan="professional")
    mock_tenant_repo.get_by_id.return_value = mock_tenant

    service = TenantService(tenant_repo=mock_tenant_repo)
    result = await service.get_tenant_by_id(mock_session, tenant_id)

    assert result == mock_tenant
    mock_tenant_repo.get_by_id.assert_awaited_once_with(mock_session, tenant_id)


@pytest.mark.asyncio
async def test_get_tenant_by_id_not_found_raises_error(
    mock_session: AsyncMock,
    mock_tenant_repo: AsyncMock,
) -> None:
    """Verify get_tenant_by_id raises TenantNotFoundError when tenant is not found."""
    mock_tenant_repo.get_by_id.return_value = None

    service = TenantService(tenant_repo=mock_tenant_repo)
    with pytest.raises(TenantNotFoundError):
        await service.get_tenant_by_id(mock_session, uuid.uuid4())


@pytest.mark.asyncio
async def test_get_tenant_by_slug_normalizes_slug(
    mock_session: AsyncMock, mock_tenant_repo: AsyncMock
) -> None:
    """Verify get_tenant_by_slug normalizes slug before querying repository."""
    mock_tenant = Tenant(id=uuid.uuid4(), name="Acme", slug="acme-corp", plan="enterprise")
    mock_tenant_repo.get_by_slug.return_value = mock_tenant

    service = TenantService(tenant_repo=mock_tenant_repo)
    result = await service.get_tenant_by_slug(mock_session, "  ACME-CORP  ")

    assert result == mock_tenant
    mock_tenant_repo.get_by_slug.assert_awaited_once_with(mock_session, "acme-corp")


@pytest.mark.asyncio
async def test_update_tenant_slug_duplicate_raises_error(
    mock_session: AsyncMock,
    mock_tenant_repo: AsyncMock,
    admin_user_id: uuid.UUID,
) -> None:
    """Verify update_tenant raises TenantSlugAlreadyExistsError if updated slug belongs to another tenant."""
    tenant_id = uuid.uuid4()
    other_tenant_id = uuid.uuid4()
    existing = Tenant(id=tenant_id, name="Old", slug="old-slug", plan="starter")
    other_tenant = Tenant(id=other_tenant_id, name="Other", slug="taken-slug", plan="starter")

    mock_tenant_repo.get_by_id.return_value = existing
    mock_tenant_repo.get_by_slug.return_value = other_tenant

    service = TenantService(tenant_repo=mock_tenant_repo)
    with pytest.raises(TenantSlugAlreadyExistsError, match="taken-slug"):
        await service.update_tenant(
            mock_session, user_id=admin_user_id, tenant_id=tenant_id, slug="TAKEN-SLUG"
        )


@pytest.mark.asyncio
async def test_update_tenant_success(
    mock_session: AsyncMock,
    mock_tenant_repo: AsyncMock,
    admin_user_id: uuid.UUID,
) -> None:
    """Verify update_tenant validates existence and delegates updates to repository."""
    tenant_id = uuid.uuid4()
    existing = Tenant(id=tenant_id, name="Old Name", slug="acme", plan="starter")
    updated = Tenant(id=tenant_id, name="New Name", slug="new-acme", plan="enterprise")
    mock_tenant_repo.get_by_id.return_value = existing
    mock_tenant_repo.get_by_slug.return_value = None
    mock_tenant_repo.update.return_value = updated

    service = TenantService(tenant_repo=mock_tenant_repo)
    result = await service.update_tenant(
        mock_session,
        user_id=admin_user_id,
        tenant_id=tenant_id,
        name="New Name",
        slug="new-acme",
        plan="enterprise",
    )

    assert result == updated
    mock_tenant_repo.update.assert_awaited_once_with(
        mock_session,
        tenant_id,
        name="New Name",
        slug="new-acme",
        plan="enterprise",
    )


@pytest.mark.asyncio
async def test_delete_tenant_success(
    mock_session: AsyncMock,
    mock_tenant_repo: AsyncMock,
    admin_user_id: uuid.UUID,
) -> None:
    """Verify delete_tenant verifies existence and deletes tenant."""
    tenant_id = uuid.uuid4()
    existing = Tenant(id=tenant_id, name="Acme", slug="acme", plan="starter")
    mock_tenant_repo.get_by_id.return_value = existing
    mock_tenant_repo.delete.return_value = True

    service = TenantService(tenant_repo=mock_tenant_repo)
    await service.delete_tenant(mock_session, user_id=admin_user_id, tenant_id=tenant_id)

    mock_tenant_repo.delete.assert_awaited_once_with(mock_session, tenant_id)
