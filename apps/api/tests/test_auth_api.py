"""Integration test suite for authentication API endpoints (login, refresh, logout)."""

from unittest.mock import AsyncMock
import uuid

from fastapi.testclient import TestClient
import pytest

from hiron.auth.router import get_auth_service
from hiron.auth.service import AccountDisabledError, AuthenticationError, AuthService
from hiron.core.database import get_db_session
from hiron.main import app
from hiron.users.models import User


@pytest.fixture
def mock_db() -> AsyncMock:
    """Fixture overriding get_db_session with AsyncMock."""
    return AsyncMock()


@pytest.fixture
def mock_auth_service() -> AsyncMock:
    """Fixture overriding get_auth_service with AsyncMock."""
    return AsyncMock(spec=AuthService)


@pytest.fixture
def client(mock_db: AsyncMock, mock_auth_service: AsyncMock) -> TestClient:
    """FastAPI TestClient with dependency overrides."""
    app.dependency_overrides[get_db_session] = lambda: mock_db
    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


# ==============================================================================
# LOGIN ENDPOINT TESTS
# ==============================================================================

def test_login_endpoint_success_and_cookie_attributes(
    client: TestClient, mock_auth_service: AsyncMock
) -> None:
    """Verify POST /api/v1/auth/login returns 200 OK and sets httpOnly, SameSite=strict refreshToken cookie."""
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = User(
        id=user_id,
        tenant_id=tenant_id,
        email="jane@acme.com",
        full_name="Jane Smith",
        role="recruiter",
        avatar_url=None,
    )
    mock_auth_service.authenticate_user.return_value = mock_user
    mock_auth_service.create_auth_tokens.return_value = ("access_jwt_123", "refresh_jwt_456")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "jane@acme.com",
            "password": "securePassword123!",
            "tenantId": str(tenant_id),
        },
    )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["accessToken"] == "access_jwt_123"
    assert data["tokenType"] == "Bearer"
    assert data["expiresIn"] == 900
    assert data["user"]["id"] == str(user_id)
    assert data["user"]["email"] == "jane@acme.com"
    assert data["user"]["tenantId"] == str(tenant_id)

    # Verify cookie security attributes
    assert "refreshToken" in response.cookies
    cookie = response.cookies.get_dict()
    assert cookie["refreshToken"] == "refresh_jwt_456"


def test_login_endpoint_invalid_credentials(client: TestClient, mock_auth_service: AsyncMock) -> None:
    """Verify POST /api/v1/auth/login returns 401 INVALID_CREDENTIALS on wrong password."""
    mock_auth_service.authenticate_user.side_effect = AuthenticationError("Invalid email or password")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "jane@acme.com",
            "password": "wrong_password",
            "tenantId": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "INVALID_CREDENTIALS"


def test_login_endpoint_account_disabled_mapping(client: TestClient, mock_auth_service: AsyncMock) -> None:
    """Verify POST /api/v1/auth/login maps AccountDisabledError to HTTP 403 ACCOUNT_DISABLED."""
    mock_auth_service.authenticate_user.side_effect = AccountDisabledError()

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "disabled@acme.com",
            "password": "Password123!",
            "tenantId": str(uuid.uuid4()),
        },
    )

    assert response.status_code == 403
    payload = response.json()
    assert payload["error"]["code"] == "ACCOUNT_DISABLED"


def test_login_endpoint_validation_error(client: TestClient) -> None:
    """Verify POST /api/v1/auth/login returns 422 VALIDATION_ERROR on missing payload fields."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "not_an_email"},
    )

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"


# ==============================================================================
# REFRESH ENDPOINT TESTS
# ==============================================================================

def test_refresh_endpoint_success(client: TestClient, mock_auth_service: AsyncMock) -> None:
    """Verify POST /api/v1/auth/refresh rotates tokens via AuthService and sets new cookie."""
    mock_auth_service.rotate_refresh_token.return_value = ("new_access_jwt", "new_refresh_jwt")
    client.cookies.set("refreshToken", "valid_old_refresh_cookie")

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["accessToken"] == "new_access_jwt"
    assert response.cookies.get("refreshToken") == "new_refresh_jwt"
    mock_auth_service.rotate_refresh_token.assert_awaited_once()


def test_refresh_endpoint_missing_cookie_returns_422(client: TestClient) -> None:
    """Verify POST /api/v1/auth/refresh treats missing cookie as 422 VALIDATION_ERROR."""
    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 422
    payload = response.json()
    assert payload["error"]["code"] == "VALIDATION_ERROR"


def test_refresh_endpoint_revoked_or_expired_token_returns_401(
    client: TestClient, mock_auth_service: AsyncMock
) -> None:
    """Verify POST /api/v1/auth/refresh returns 401 when AuthService.rotate_refresh_token raises AuthenticationError."""
    mock_auth_service.rotate_refresh_token.side_effect = AuthenticationError("Invalid or expired refresh token")
    client.cookies.set("refreshToken", "revoked_or_expired_cookie")

    response = client.post("/api/v1/auth/refresh")

    assert response.status_code == 401
    payload = response.json()
    assert payload["error"]["code"] == "INVALID_CREDENTIALS"


# ==============================================================================
# LOGOUT ENDPOINT TESTS
# ==============================================================================

def test_logout_endpoint_success(client: TestClient, mock_auth_service: AsyncMock) -> None:
    """Verify POST /api/v1/auth/logout invokes AuthService.logout and returns 204 No Content."""
    client.cookies.set("refreshToken", "active_session_cookie")

    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    mock_auth_service.logout.assert_awaited_once()


def test_logout_endpoint_without_cookie_success(client: TestClient, mock_auth_service: AsyncMock) -> None:
    """Verify POST /api/v1/auth/logout without cookie calls AuthService.logout and returns 204 No Content."""
    response = client.post("/api/v1/auth/logout")

    assert response.status_code == 204
    mock_auth_service.logout.assert_awaited_once()
