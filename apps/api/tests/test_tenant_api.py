"""Integration test suite for Tenant API endpoints, verifying authentication and RBAC dependency resolution."""

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from hiron.auth.dependencies import get_current_user
from hiron.common.exceptions import register_exception_handlers
from hiron.core.database import get_db_session
from hiron.tenants.models import Tenant
from hiron.tenants.router import get_tenant_service, router as tenants_router
from hiron.tenants.service import TenantNotFoundError, TenantService
from hiron.users.models import User


@pytest.fixture
def mock_db() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_tenant_service() -> AsyncMock:
    """Fixture providing a mock TenantService."""
    return AsyncMock(spec=TenantService)


@pytest.fixture
def mock_admin_user() -> User:
    """Fixture providing a mock User entity with role='org_admin'."""
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="admin@acme.com",
        full_name="Admin User",
        role="org_admin",
        is_active=True,
    )


@pytest.fixture
def mock_recruiter_user() -> User:
    """Fixture providing a mock User entity with role='recruiter'."""
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="recruiter@acme.com",
        full_name="Recruiter User",
        role="recruiter",
        is_active=True,
    )


@pytest.fixture
def client(
    mock_db: AsyncMock, mock_tenant_service: AsyncMock, mock_admin_user: User
) -> Generator[TestClient, None, None]:
    """FastAPI TestClient testing tenants_router with get_current_user override.

    Architectural Dependency Resolution Justification:
    ---------------------------------------------------
    - Endpoints decorated with `dependencies=[Depends(require_role("org_admin"))]` invoke
      a `RoleChecker` instance returned by `require_role()`.
    - `RoleChecker.__call__` accepts `current_user: Annotated[User, Depends(get_current_user)]`.
    - Because FastAPI recursively inspects callable parameter dependencies, overriding `get_current_user`
      in `dependency_overrides[get_current_user]` causes FastAPI to supply `mock_admin_user`
      to `RoleChecker.__call__`.
    - Since `mock_admin_user.role` is `"org_admin"`, `current_user.role in self.allowed_roles` evaluates
      to `True`, satisfying the RBAC check without needing to override the `RoleChecker` instance.
    """
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(tenants_router, prefix="/api/v1/tenants")

    test_app.dependency_overrides[get_db_session] = lambda: mock_db
    test_app.dependency_overrides[get_tenant_service] = lambda: mock_tenant_service
    test_app.dependency_overrides[get_current_user] = lambda: mock_admin_user

    with TestClient(test_app) as test_client:
        yield test_client

    test_app.dependency_overrides.clear()


def test_create_tenant_endpoint_success(client: TestClient, mock_tenant_service: AsyncMock) -> None:
    """Verify POST /api/v1/tenants creates tenant and returns 201 Created envelope for org_admin user."""
    tenant_id = uuid.uuid4()
    now = datetime.now(UTC)
    mock_tenant = Tenant(
        id=tenant_id,
        name="Acme Corp",
        slug="acme-corp",
        plan="starter",
        settings={},
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    mock_tenant_service.create_tenant.return_value = mock_tenant

    response = client.post(
        "/api/v1/tenants",
        json={"name": "Acme Corp", "slug": "acme-corp", "plan": "starter"},
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id"] == str(tenant_id)
    assert data["name"] == "Acme Corp"
    assert data["slug"] == "acme-corp"


def test_list_tenants_endpoint_success(client: TestClient, mock_tenant_service: AsyncMock) -> None:
    """Verify GET /api/v1/tenants returns active tenants list for org_admin user."""
    now = datetime.now(UTC)
    t1 = Tenant(
        id=uuid.uuid4(),
        name="T1",
        slug="t1",
        plan="starter",
        settings={},
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    mock_tenant_service.list_active_tenants.return_value = [t1]

    response = client.get("/api/v1/tenants")

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["slug"] == "t1"


def test_get_tenant_endpoint_success(
    client: TestClient, mock_tenant_service: AsyncMock, mock_admin_user: User
) -> None:
    """Verify GET /api/v1/tenants/{id} returns tenant details for authenticated user."""
    tenant_id = mock_admin_user.tenant_id
    now = datetime.now(UTC)
    mock_tenant = Tenant(
        id=tenant_id,
        name="Acme",
        slug="acme",
        plan="enterprise",
        settings={},
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    mock_tenant_service.get_tenant_by_id.return_value = mock_tenant

    response = client.get(f"/api/v1/tenants/{tenant_id}")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(tenant_id)


def test_get_tenant_not_found(
    client: TestClient, mock_tenant_service: AsyncMock, mock_admin_user: User
) -> None:
    """Verify GET /api/v1/tenants/{id} returns 404 when tenant is missing."""
    mock_tenant_service.get_tenant_by_id.side_effect = TenantNotFoundError()

    response = client.get(f"/api/v1/tenants/{mock_admin_user.tenant_id}")

    assert response.status_code == 404
    payload = response.json()
    assert payload["error"]["code"] == "TENANT_NOT_FOUND"


def test_update_tenant_endpoint_success(
    client: TestClient, mock_tenant_service: AsyncMock, mock_admin_user: User
) -> None:
    """Verify PATCH /api/v1/tenants/{id} updates tenant and returns 200 OK for org_admin user."""
    tenant_id = mock_admin_user.tenant_id
    now = datetime.now(UTC)
    updated = Tenant(
        id=tenant_id,
        name="Acme Inc",
        slug="acme",
        plan="professional",
        settings={},
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    mock_tenant_service.update_tenant.return_value = updated

    response = client.patch(
        f"/api/v1/tenants/{tenant_id}", json={"name": "Acme Inc", "plan": "professional"}
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["name"] == "Acme Inc"


def test_delete_tenant_endpoint_success(
    client: TestClient, mock_tenant_service: AsyncMock, mock_admin_user: User
) -> None:
    """Verify DELETE /api/v1/tenants/{id} returns 204 No Content for org_admin user."""
    tenant_id = mock_admin_user.tenant_id

    response = client.delete(f"/api/v1/tenants/{tenant_id}")

    assert response.status_code == 204
    mock_tenant_service.delete_tenant.assert_awaited_once()


def test_tenant_api_rbac_forbidden_for_non_admin(
    mock_db: AsyncMock,
    mock_tenant_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify that a non-org_admin user (e.g. recruiter) receives 403 Forbidden when invoking RBAC-protected routes."""
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(tenants_router, prefix="/api/v1/tenants")

    test_app.dependency_overrides[get_db_session] = lambda: mock_db
    test_app.dependency_overrides[get_tenant_service] = lambda: mock_tenant_service
    test_app.dependency_overrides[get_current_user] = lambda: mock_recruiter_user

    with TestClient(test_app) as client:
        response = client.post(
            "/api/v1/tenants",
            json={"name": "Forbidden Corp", "slug": "forbidden-corp"},
        )
        assert response.status_code == 403
        payload = response.json()
        assert payload["error"]["code"] == "INSUFFICIENT_PERMISSIONS"


def test_tenant_api_cross_tenant_forbidden(client: TestClient, mock_tenant_service: AsyncMock) -> None:
    """Verify that an org_admin cannot access or update another tenant's data."""
    other_tenant_id = uuid.uuid4()

    # 1. Test GET cross-tenant
    response = client.get(f"/api/v1/tenants/{other_tenant_id}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"

    # 2. Test PATCH cross-tenant
    response = client.patch(
        f"/api/v1/tenants/{other_tenant_id}",
        json={"name": "Hacked Tenant"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"
    mock_tenant_service.update_tenant.assert_not_awaited()

    # 3. Test DELETE cross-tenant
    response = client.delete(f"/api/v1/tenants/{other_tenant_id}")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"
    mock_tenant_service.delete_tenant.assert_not_awaited()
