"""Integration test suite for User API endpoints, verifying authentication and RBAC permissions."""

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
from hiron.users.models import User
from hiron.users.router import get_user_service, router as users_router


@pytest.fixture
def mock_db() -> AsyncMock:
    """Fixture providing a mock AsyncSession."""
    return AsyncMock()


@pytest.fixture
def mock_user_service() -> AsyncMock:
    """Fixture providing a mock UserService."""
    return AsyncMock()


@pytest.fixture
def mock_admin_user() -> User:
    """Fixture providing an org_admin User entity."""
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="admin@acme.com",
        full_name="Admin User",
        role="org_admin",
        is_active=True,
        is_email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def mock_recruiter_user() -> User:
    """Fixture providing a recruiter User entity."""
    return User(
        id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        email="recruiter@acme.com",
        full_name="Recruiter User",
        role="recruiter",
        is_active=True,
        is_email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture
def client(
    mock_db: AsyncMock,
    mock_user_service: AsyncMock,
    mock_admin_user: User,
) -> Generator[TestClient, None, None]:
    """FastAPI TestClient with dependency overrides for org_admin user."""
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(users_router, prefix="/api/v1/users")

    test_app.dependency_overrides[get_db_session] = lambda: mock_db
    test_app.dependency_overrides[get_user_service] = lambda: mock_user_service
    test_app.dependency_overrides[get_current_user] = lambda: mock_admin_user

    with TestClient(test_app) as test_client:
        yield test_client


def test_list_users_endpoint_success(
    client: TestClient, mock_user_service: AsyncMock, mock_admin_user: User
) -> None:
    """Verify GET /api/v1/users returns 200 OK and list of users."""
    u1 = User(
        id=uuid.uuid4(),
        tenant_id=mock_admin_user.tenant_id,
        email="u1@acme.com",
        full_name="User One",
        role="recruiter",
        is_active=True,
        is_email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_user_service.list_users.return_value = ([u1], 1)

    response = client.get("/api/v1/users")
    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["email"] == "u1@acme.com"


def test_get_user_endpoint_success(
    client: TestClient, mock_user_service: AsyncMock, mock_admin_user: User
) -> None:
    """Verify GET /api/v1/users/{user_id} returns 200 OK and user payload."""
    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        tenant_id=mock_admin_user.tenant_id,
        email="target@acme.com",
        full_name="Target User",
        role="hiring_manager",
        is_active=True,
        is_email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_user_service.get_user_by_id.return_value = mock_user

    response = client.get(f"/api/v1/users/{user_id}")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == str(user_id)
    assert data["email"] == "target@acme.com"


def test_create_user_endpoint_success(
    client: TestClient, mock_user_service: AsyncMock, mock_admin_user: User
) -> None:
    """Verify POST /api/v1/users returns 201 Created and newly created user payload."""
    new_id = uuid.uuid4()
    created_user = User(
        id=new_id,
        tenant_id=mock_admin_user.tenant_id,
        email="newuser@acme.com",
        full_name="New Recruiter",
        role="recruiter",
        is_active=True,
        is_email_verified=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_user_service.create_user.return_value = created_user

    response = client.post(
        "/api/v1/users",
        json={
            "email": "newuser@acme.com",
            "fullName": "New Recruiter",
            "role": "recruiter",
        },
    )

    assert response.status_code == 201
    data = response.json()["data"]
    assert data["id"] == str(new_id)
    assert data["role"] == "recruiter"


def test_update_user_endpoint_success(
    client: TestClient, mock_user_service: AsyncMock, mock_admin_user: User
) -> None:
    """Verify PATCH /api/v1/users/{user_id} returns 200 OK and updated user payload."""
    user_id = uuid.uuid4()
    updated_user = User(
        id=user_id,
        tenant_id=mock_admin_user.tenant_id,
        email="user@acme.com",
        full_name="Updated Name",
        role="org_admin",
        is_active=True,
        is_email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_user_service.update_user.return_value = updated_user

    response = client.patch(
        f"/api/v1/users/{user_id}",
        json={"fullName": "Updated Name", "role": "org_admin"},
    )
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["fullName"] == "Updated Name"


def test_deactivate_user_endpoint_success(
    client: TestClient, mock_user_service: AsyncMock, mock_admin_user: User
) -> None:
    """Verify POST /api/v1/users/{user_id}/deactivate returns 200 OK."""
    user_id = uuid.uuid4()
    deactivated_user = User(
        id=user_id,
        tenant_id=mock_admin_user.tenant_id,
        email="user@acme.com",
        full_name="User Name",
        role="recruiter",
        is_active=False,
        is_email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    mock_user_service.deactivate_user.return_value = deactivated_user

    response = client.post(f"/api/v1/users/{user_id}/deactivate")
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["isActive"] is False


def test_delete_user_endpoint_success(client: TestClient, mock_user_service: AsyncMock) -> None:
    """Verify DELETE /api/v1/users/{user_id} returns 204 No Content."""
    user_id = uuid.uuid4()
    mock_user_service.delete_user.return_value = None

    response = client.delete(f"/api/v1/users/{user_id}")
    assert response.status_code == 204


def test_user_api_rbac_forbidden_for_non_admin(
    mock_db: AsyncMock,
    mock_user_service: AsyncMock,
    mock_recruiter_user: User,
) -> None:
    """Verify non-admin user receives 403 Forbidden when accessing admin-only user creation endpoint."""
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(users_router, prefix="/api/v1/users")

    test_app.dependency_overrides[get_db_session] = lambda: mock_db
    test_app.dependency_overrides[get_user_service] = lambda: mock_user_service
    test_app.dependency_overrides[get_current_user] = lambda: mock_recruiter_user

    with TestClient(test_app) as recruiter_client:
        response = recruiter_client.post(
            "/api/v1/users",
            json={
                "email": "another@acme.com",
                "fullName": "Another User",
                "role": "recruiter",
            },
        )
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "INSUFFICIENT_PERMISSIONS"
